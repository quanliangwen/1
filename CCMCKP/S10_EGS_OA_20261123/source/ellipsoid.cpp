#include "ellipsoid.hpp"
#include <gurobi_c.h>
#include <cmath>
#include <limits>
#include <set>
#include <tuple>

namespace s10 {
double ellipsoid_norm(const Instance& instance, const Selection& selection) {
    instance.validate(selection);
    double norm = 0;
    for (int j : selection) norm = std::hypot(norm, std::sqrt(instance.variance[j]));
    return norm;
}

double ellipsoid_risk(const Instance& instance, const Selection& selection, double gamma) {
    Vector means;
    for (int j : selection) means.push_back(instance.mean[j]);
    return sum(means) + gamma * ellipsoid_norm(instance, selection);
}

Json EllipsoidQuery::json() const {
    return {{"has_candidate", has_candidate}, {"unvisited_domain_exhausted", exhausted},
        {"cone_converged", cone_converged}, {"proxy_optimal", proxy_optimal},
        {"selection", selection}, {"cost", cost}, {"risk", risk}, {"norm", norm},
        {"epigraph", epigraph}, {"proxy_objective_bound", objective_bound},
        {"gurobi_status", status}, {"optimize_calls", optimize_calls},
        {"cuts_added", cuts_added}, {"seconds", seconds},
        {"bound_scope", "unvisited_ellipsoid_proxy_only_not_CCMCKP_cost"}};
}

struct EllipsoidMaster::Impl {
    const Instance& instance;
    double gamma;
    struct EnvDelete { void operator()(GRBenv* p) const { if (p) GRBfreeenv(p); } };
    struct ModelDelete { void operator()(GRBmodel* p) const { if (p) GRBfreemodel(p); } };
    std::unique_ptr<GRBenv, EnvDelete> environment;
    std::unique_ptr<GRBmodel, ModelDelete> model;
    std::set<Selection> supports, exclusions;
    double cost_bound = std::numeric_limits<double>::infinity();
    int cost_row = -1, cuts = 0;

    void check(int code) {
        if (code) throw std::runtime_error("Ellipsoid Gurobi error " + std::to_string(code) + ": " +
            (model ? GRBgeterrormsg(GRBgetenv(model.get())) :
             environment ? GRBgeterrormsg(environment.get()) : "environment creation failed"));
    }

    Impl(const Instance& data, int seed, double radius) : instance(data), gamma(radius) {
        if (!(std::isfinite(gamma) && gamma >= 0)) throw std::invalid_argument("Invalid ellipsoid gamma");
        GRBenv* env = nullptr;
        const int code = GRBemptyenv(&env);
        environment.reset(env);
        check(code);
        check(GRBsetintparam(env, "OutputFlag", 0));
        check(GRBstartenv(env));
        Vector objective = instance.mean;
        objective.push_back(gamma);
        std::vector<char> types(instance.n() + 1, GRB_BINARY);
        types.back() = GRB_CONTINUOUS;
        Vector lower(instance.n() + 1, 0), upper(instance.n() + 1, 1);
        upper.back() = GRB_INFINITY;
        GRBmodel* raw = nullptr;
        const int create = GRBnewmodel(env, &raw, "EGS_ellipsoid_proxy", instance.n() + 1,
            objective.data(), lower.data(), upper.data(), types.data(), nullptr);
        model.reset(raw);
        check(create);
        auto* params = GRBgetenv(raw);
        check(GRBsetintparam(params, "Threads", 1));
        check(GRBsetintparam(params, "Seed", seed));
        check(GRBsetdblparam(params, "MIPGap", 0));
        check(GRBsetdblparam(params, "FeasibilityTol", 1e-9));
        check(GRBsetdblparam(params, "IntFeasTol", 1e-9));
        for (const auto& group : instance.groups) {
            auto indices = group;
            Vector values(group.size(), 1);
            check(GRBaddconstr(raw, static_cast<int>(indices.size()), indices.data(), values.data(),
                GRB_EQUAL, 1, nullptr));
        }
        Selection indices(instance.n());
        for (int j = 0; j < instance.n(); ++j) indices[j] = j;
        auto costs = instance.costs;
        check(GRBaddconstr(raw, instance.n(), indices.data(), costs.data(), GRB_LESS_EQUAL,
            GRB_INFINITY, "candidate_cost_bound"));
        cost_row = instance.m();
        // Axis directions are valid initial SOC support cuts, not chance constraints.
        if (gamma > 0) {
            for (int j = 0; j < instance.n(); ++j) {
                if (instance.variance[j] == 0) continue;
                int pair[] = {j, instance.n()};
                double values[] = {std::sqrt(instance.variance[j]), -1};
                check(GRBaddconstr(raw, 2, pair, values, GRB_LESS_EQUAL, 0, nullptr));
                ++cuts;
            }
        }
        check(GRBupdatemodel(raw));
    }

    bool add_support(const Selection& selection) {
        instance.validate(selection);
        if (gamma == 0 || supports.count(selection)) return false;
        const double norm = ellipsoid_norm(instance, selection);
        if (norm == 0) return false;
        Selection indices = selection;
        Vector coefficients;
        for (int j : selection) coefficients.push_back(instance.variance[j] / norm);
        indices.push_back(instance.n());
        coefficients.push_back(-1);
        check(GRBaddconstr(model.get(), static_cast<int>(indices.size()), indices.data(),
            coefficients.data(), GRB_LESS_EQUAL, 0, nullptr));
        supports.insert(selection);
        ++cuts;
        return true;
    }
};

EllipsoidMaster::EllipsoidMaster(const Instance& instance, int seed, double gamma)
    : impl(new Impl(instance, seed, gamma)) {}
EllipsoidMaster::~EllipsoidMaster() = default;

void EllipsoidMaster::set_cost_bound(double bound) {
    if (!std::isfinite(bound) || bound > impl->cost_bound)
        throw std::invalid_argument("Candidate cost bound must be finite and must not loosen");
    impl->check(GRBsetdblattrelement(impl->model.get(), "RHS", impl->cost_row, bound));
    impl->cost_bound = bound;
}

bool EllipsoidMaster::exclude_processed(const Selection& selection) {
    impl->instance.validate(selection);
    if (impl->exclusions.count(selection)) return false;
    auto indices = selection;
    Vector values(selection.size(), 1);
    impl->check(GRBaddconstr(impl->model.get(), static_cast<int>(indices.size()), indices.data(),
        values.data(), GRB_LESS_EQUAL, impl->instance.m() - 1, nullptr));
    impl->exclusions.insert(selection);
    return true;
}

bool EllipsoidMaster::add_support_cut(const Selection& selection) { return impl->add_support(selection); }
int EllipsoidMaster::cut_count() const { return impl->cuts; }
int EllipsoidMaster::excluded_count() const { return static_cast<int>(impl->exclusions.size()); }

EllipsoidQuery EllipsoidMaster::next_candidate(double seconds) {
    EllipsoidQuery result;
    const double started = now(), deadline = started + seconds;
    const int prior_cuts = impl->cuts;
    while (now() + .005 < deadline) {
        auto* m = impl->model.get();
        impl->check(GRBsetdblparam(GRBgetenv(m), "TimeLimit", std::max(.001, deadline - now())));
        impl->check(GRBoptimize(m));
        ++result.optimize_calls;
        int status = 0, count = 0;
        impl->check(GRBgetintattr(m, "Status", &status));
        impl->check(GRBgetintattr(m, "SolCount", &count));
        result.status = status;
        if (status == GRB_INFEASIBLE) { result.exhausted = true; break; }
        if (!count) break;
        Vector x(impl->instance.n() + 1);
        impl->check(GRBgetdblattrarray(m, "X", 0, static_cast<int>(x.size()), x.data()));
        Selection selection;
        for (const auto& group : impl->instance.groups) {
            const int j = *std::max_element(group.begin(), group.end(),
                [&](int a, int b) { return x[a] < x[b]; });
            if (x[j] < 1 - 1e-6) throw std::runtime_error("Nonintegral candidate returned by Gurobi");
            selection.push_back(j);
        }
        const double cost = impl->instance.cost_of(selection);
        const double norm = ellipsoid_norm(impl->instance, selection);
        const double risk = ellipsoid_risk(impl->instance, selection, impl->gamma);
        const bool converged = impl->gamma == 0 || x.back() + 1e-8 * std::max(1., norm) >= norm;
        double bound = 0;
        impl->check(GRBgetdblattr(m, "ObjBound", &bound));
        // Check the actual discrete vector, not just the solver's rounded row activity.
        if (!impl->exclusions.count(selection) && cost <= impl->cost_bound + 1e-9) {
            if (!result.has_candidate || std::make_tuple(risk, cost, selection) <
                std::make_tuple(result.risk, result.cost, result.selection)) {
                result.has_candidate = true;
                result.selection = selection;
                result.cost = cost;
                result.risk = risk;
                result.norm = norm;
                result.epigraph = x.back();
                result.cone_converged = converged;
                result.objective_bound = bound;
            }
            if (converged && status == GRB_OPTIMAL) {
                result.selection = selection;
                result.cost = cost;
                result.risk = risk;
                result.norm = norm;
                result.epigraph = x.back();
                result.cone_converged = true;
                result.objective_bound = bound;
                result.proxy_optimal = true;
                break;
            }
        }
        if (converged || !impl->add_support(selection)) break;
    }
    result.seconds = now() - started;
    result.cuts_added = impl->cuts - prior_cuts;
    return result;
}
} // namespace s10
