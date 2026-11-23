#pragma once
#include "model.hpp"
#include <memory>

namespace s10 {
// Candidate-generator risk only. Neither this value nor its cuts certify P>=.99.
double ellipsoid_norm(const Instance& instance, const Selection& selection);
double ellipsoid_risk(const Instance& instance, const Selection& selection, double gamma);

struct EllipsoidQuery {
    bool has_candidate = false;
    bool exhausted = false;
    bool cone_converged = false;
    bool proxy_optimal = false;
    Selection selection;
    double cost = 0, risk = 0, norm = 0, epigraph = 0, objective_bound = 0;
    int status = 0, optimize_calls = 0, cuts_added = 0;
    double seconds = 0;
    Json json() const;
};

class EllipsoidMaster {
public:
    EllipsoidMaster(const Instance& instance, int seed, double gamma);
    ~EllipsoidMaster();
    // Bounds may only tighten. The budget is for searching improving candidates.
    void set_cost_bound(double bound);
    bool exclude_processed(const Selection& selection);
    bool add_support_cut(const Selection& selection);
    EllipsoidQuery next_candidate(double seconds);
    int cut_count() const;
    int excluded_count() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl;
};
} // namespace s10
