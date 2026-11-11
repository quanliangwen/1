#pragma once
#include "evaluation.hpp"
#include "mip.hpp"
#include <map>
#include <complex>
#include <optional>
#include <set>

namespace s10 {
struct Options {
    double capacity;
    std::string capacity_text;
    std::uint32_t seed;
    double seconds;
    std::string backend, local_phases;
    fs::path output;
};

class Search {
public:
    Search(const Instance& instance, Options options, double started);
    Json run();
    Json phase_records = Json::array();
    const Groups& quick_checks() const { return checks; }
    const std::vector<std::uint16_t>& screen_indices() const { return indices; }
private:
    struct Candidate {
        Selection selection;
        double cost;
        Certificate certificate;
        std::string source;
        double found_seconds;
        Json json() const;
    };
    struct HalfState {
        double cost;
        float p0, p1;
        std::vector<float> pdf;
        Selection selection;
    };

    const Instance& instance;
    Options options;
    double started, deadline;
    ExactOracle oracle;
    BinaryModel model;
    Groups checks;
    std::vector<std::uint16_t> indices;
    std::map<Selection, Candidate> pool;
    std::map<Selection, double> decisions, guide_cache;
    std::set<Selection> frontier_candidates;
    std::optional<Candidate> best;
    std::vector<Vector> guide_hist;
    std::vector<std::vector<std::complex<double>>> guide_fft;
    Vector guide_weight;
    Json exhaustive, events = Json::array(), matches = Json::array(), locals = Json::array();
    bool recomputed = false;
    int models = 0;
    double model_seconds = 0, last_save = 0;

    double remaining() const { return deadline - now(); }
    Groups binary(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int count);
    Groups mip(const Vector& weights, double rhs, std::optional<double> vcap,
               int trust, const Selection& center, double seconds, int count);
    Selection minimum(const Vector& objective) const;
    Groups cost_order(const std::set<Selection>& selections) const;
    double accept(const Selection& selection, std::string source, const Certificate& certificate);
    double native_check(const Selection& selection, const std::string& source);
    std::pair<double, double> float_bounds(const Selection& selection, int bins);
    void small_exact_search();
    void init_frontier();
    void local_search(double seconds);
    void matching(double delta, const Selection& left, const Selection& right);
    std::vector<HalfState> build_half(const Selection& groups, const Selection& other,
                                    const std::vector<std::vector<float>>& hist);
    std::vector<HalfState> prune(std::vector<HalfState> states) const;
    std::vector<Vector> histograms(int bins, double delta) const;
    std::pair<double, Vector> gradients(const Selection& selection);
    double guide_probability(const Selection& selection);
    Json shortlist() const;
    Json save(const std::string& status);
    void final_check();
};
} // namespace s10
