#include "mip.hpp"
#include <cmath>
#include <gurobi_c.h>

namespace s10 {
struct BinaryModel::Impl {
    const Instance& instance;
    int seed;
    struct EnvDeleter { void operator()(GRBenv* e) const { GRBfreeenv(e); } };
    struct ModelDeleter { void operator()(GRBmodel* m) const { GRBfreemodel(m); } };
    std::unique_ptr<GRBenv, EnvDeleter> env;

    void gurobi_check(int code, GRBenv* e) {
        if (code) throw std::runtime_error("Gurobi error " + std::to_string(code) + ": " +
                                          (e ? GRBgeterrormsg(e) : "environment creation failed"));
    }

    Groups solve(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool) {
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
    Selection selection(const Vector& x) const {
        Selection result;
        for (const auto& group : instance.groups)
            result.push_back(*std::max_element(group.begin(), group.end(), [&](int a, int b) { return x[a] < x[b]; }));
        return result;
    }
};

BinaryModel::BinaryModel(const Instance& instance, int seed)
    : impl(new Impl{instance, seed, {}}) {}
BinaryModel::~BinaryModel() = default;

Groups BinaryModel::solve(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool) {
    return impl->solve(objective, rows, seconds, pool);
}
} // namespace s10
