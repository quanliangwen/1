#include "mip.hpp"
#include <cmath>
#include <numeric>
#ifdef S10_HAS_GUROBI
#include <gurobi_c.h>
#endif
#ifdef S10_HAS_HIGHS
#include <Highs.h>
#endif

namespace s10 {
struct BinaryModel::Impl {
    const Instance& instance;
    std::string backend;
    int seed;
#ifdef S10_HAS_GUROBI
    struct EnvDeleter { void operator()(GRBenv* e) const { GRBfreeenv(e); } };
    struct ModelDeleter { void operator()(GRBmodel* m) const { GRBfreemodel(m); } };
    std::unique_ptr<GRBenv, EnvDeleter> env;

    void gurobi_check(int code, GRBenv* e) {
        if (code) throw std::runtime_error("Gurobi error " + std::to_string(code) + ": " +
                                          (e ? GRBgeterrormsg(e) : "environment creation failed"));
    }

    Groups gurobi(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool) {
        if (!env) {
            GRBenv* e = nullptr;
            const int status = GRBemptyenv(&e);
            env.reset(e);
            gurobi_check(status, e);
            gurobi_check(GRBsetintparam(e, "OutputFlag", 0), e);
            gurobi_check(GRBstartenv(e), e);
        }
        GRBmodel* m = nullptr;
        std::vector<char> types(instance.n(), GRB_BINARY);
        auto costs = objective;
        const int status = GRBnewmodel(env.get(), &m, "S10", instance.n(), costs.data(),
                                       nullptr, nullptr, types.data(), nullptr);
        std::unique_ptr<GRBmodel, ModelDeleter> model(m);
        gurobi_check(status, env.get());
        auto* params = GRBgetenv(m);
        const auto check = [&](int code) { gurobi_check(code, params); };
        check(GRBsetintparam(params, "Threads", 1));
        check(GRBsetintparam(params, "Seed", seed));
        check(GRBsetdblparam(params, "MIPGap", 0.));
        const auto add = [&](Selection indices, Vector values, char sense, double rhs) {
            check(GRBaddconstr(m, static_cast<int>(indices.size()), indices.data(), values.data(), sense, rhs, nullptr));
        };
        for (const auto& group : instance.groups) add(group, Vector(group.size(), 1), GRB_EQUAL, 1);
        for (const auto& row : rows) {
            Selection indices;
            Vector values;
            for (int j = 0; j < instance.n(); ++j)
                if (row.coefficients[j]) { indices.push_back(j); values.push_back(row.coefficients[j]); }
            if (std::isfinite(row.lower)) add(indices, values, GRB_GREATER_EQUAL, row.lower);
            if (std::isfinite(row.upper)) add(indices, values, GRB_LESS_EQUAL, row.upper);
        }
        const double deadline = now() + seconds;
        Groups result;
        for (int i = 0; i < pool; ++i) {
            const double left = deadline - now();
            if (left <= .005) break;
            check(GRBsetdblparam(params, "TimeLimit", left));
            check(GRBoptimize(m));
            int count = 0;
            check(GRBgetintattr(m, "SolCount", &count));
            if (!count) break;
            Vector values(instance.n());
            check(GRBgetdblattrarray(m, "X", 0, instance.n(), values.data()));
            auto s = selection(values);
            add(s, Vector(s.size(), 1), GRB_LESS_EQUAL, instance.m() - 1);
            check(GRBreset(m, 0));
            result.push_back(std::move(s));
        }
        return result;
    }
#endif
#ifdef S10_HAS_HIGHS
    Groups highs(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool) {
        HighsLp model;
        const int n = instance.n();
        model.num_col_ = n;
        model.col_cost_ = objective;
        model.col_lower_.assign(n, 0);
        model.col_upper_.assign(n, 1);
        model.integrality_.assign(n, HighsVarType::kInteger);
        model.a_matrix_.format_ = MatrixFormat::kRowwise;
        model.a_matrix_.start_.assign(1, 0);
        const auto add = [&](const Selection& indices, const Vector& values, double lo, double hi) {
            model.a_matrix_.index_.insert(model.a_matrix_.index_.end(), indices.begin(), indices.end());
            model.a_matrix_.value_.insert(model.a_matrix_.value_.end(), values.begin(), values.end());
            model.a_matrix_.start_.push_back(static_cast<HighsInt>(model.a_matrix_.index_.size()));
            model.row_lower_.push_back(lo);
            model.row_upper_.push_back(hi);
        };
        for (const auto& group : instance.groups) {
            auto ids = group;
            std::sort(ids.begin(), ids.end());
            add(ids, Vector(ids.size(), 1), 1, 1);
        }
        for (const auto& row : rows) {
            Selection indices;
            Vector values;
            for (int j = 0; j < n; ++j)
                if (row.coefficients[j]) { indices.push_back(j); values.push_back(row.coefficients[j]); }
            add(indices, values, row.lower, row.upper);
        }
        const double deadline = now() + seconds;
        Groups result;
        for (int i = 0; i < pool; ++i) {
            const double left = deadline - now();
            if (left <= .005) break;
            model.num_row_ = static_cast<HighsInt>(model.row_lower_.size());
            model.a_matrix_.num_row_ = model.num_row_;
            model.a_matrix_.num_col_ = n;
            Highs solver;
            solver.setOptionValue("output_flag", false);
            solver.setOptionValue("threads", 1);
            solver.setOptionValue("random_seed", seed);
            solver.setOptionValue("mip_rel_gap", 0.);
            solver.setOptionValue("time_limit", left);
            if (solver.passModel(model) == HighsStatus::kError || solver.run() == HighsStatus::kError)
                throw std::runtime_error("HiGHS could not solve the S10 binary model");
            if (solver.getInfo().primal_solution_status != kSolutionStatusFeasible) break;
            auto s = selection(solver.getSolution().col_value);
            auto ids = s;
            std::sort(ids.begin(), ids.end());
            add(ids, Vector(ids.size(), 1), -kHighsInf, instance.m() - 1);
            result.push_back(std::move(s));
        }
        return result;
    }
#endif
    Selection selection(const Vector& x) const {
        Selection result;
        for (const auto& group : instance.groups)
            result.push_back(*std::max_element(group.begin(), group.end(), [&](int a, int b) { return x[a] < x[b]; }));
        return result;
    }
};

BinaryModel::BinaryModel(const Instance& instance, std::string backend, int seed)
    : impl(new Impl{instance, std::move(backend), seed
#ifdef S10_HAS_GUROBI
                    , {}
#endif
                    }) {}
BinaryModel::~BinaryModel() = default;

Groups BinaryModel::solve(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool) {
    if (impl->backend == "gurobi") {
#ifdef S10_HAS_GUROBI
        return impl->gurobi(objective, rows, seconds, pool);
#else
        throw std::runtime_error("This build needs the native Gurobi SDK for the frozen G_NONE arm");
#endif
    }
#ifdef S10_HAS_HIGHS
    return impl->highs(objective, rows, seconds, pool);
#else
    throw std::runtime_error("This build does not include native HiGHS");
#endif
}
} // namespace s10
