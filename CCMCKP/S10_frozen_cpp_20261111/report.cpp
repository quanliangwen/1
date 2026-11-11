#include "report.hpp"
#include "normal.hpp"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <sstream>
#include <tuple>

namespace s10 {
namespace {
using ccmckp::LegacyRandom;

double log_phi(double x) {
    constexpr double sqrt2 = 1.41421356237309504880;
    if (x > 0) return std::log1p(-.5 * std::erfc(x / sqrt2));
    if (x > -37) return std::log(.5 * std::erfc(-x / sqrt2));
    if (std::isinf(x)) return x;
    // Mills ratio expansion in the far left tail.
    const double inv = 1 / (x * x);
    const double correction = inv * (-1 + inv * (3 + inv * (-15 + inv * (105 + inv * (-945 + inv * 10395)))));
    return -.5 * x * x - std::log(-x) - .91893853320467274178 + std::log1p(correction);
}

double log_add(double a, double b) {
    if (a < b) std::swap(a, b);
    return a == -std::numeric_limits<double>::infinity() ? a : a + std::log1p(std::exp(b - a));
}

class TruncatedNormal {
public:
    TruncatedNormal(double mean, double deviation, double ceiling)
        : mean(mean), deviation(deviation) {
        const double a = -mean / deviation, b = (ceiling - mean) / deviation;
        if (!(deviation > 0 && a < b)) throw std::runtime_error("Invalid truncated-normal parameters");
        right = a >= 0;
        if (b <= 0 || a > 0) {
            const double hi = log_phi(b <= 0 ? b : -a);
            const double lo = log_phi(b <= 0 ? a : -b);
            log_mass = hi + std::log(-std::expm1(lo - hi));
        } else {
            constexpr double sqrt2 = 1.41421356237309504880;
            log_mass = std::log1p(-.5 * std::erfc(-a / sqrt2) - .5 * std::erfc(b / sqrt2));
        }
        edge = log_phi(right ? -b : a);
    }

    double draw(LegacyRandom& rng) const {
        const double u = rng.uniform();
        const double log_p = log_add(edge, (right ? std::log1p(-u) : std::log(u)) + log_mass);
        const double z = normal_inverse_log(log_p);
        return (right ? -z : z) * deviation + mean;
    }
private:
    double mean, deviation, log_mass, edge;
    bool right;
};

struct Distribution {
    std::string name;
    double mean, variance;
    int component = 0;
};

Distribution load_distribution(const fs::path& file) {
    std::ifstream input(file);
    if (!input) throw std::runtime_error("Cannot read " + file.string());
    std::vector<std::string> values;
    for (std::string line; std::getline(input, line);) {
        std::istringstream words(line);
        std::string label, value;
        if (words >> label >> value) values.push_back(value);
    }
    Distribution d{values.at(0), std::stod(values.at(1)), std::stod(values.at(2))};
    if (d.name == "bimodal") d.component = std::stoi(values.at(5));
    return d;
}

Vector draw_factor(const Distribution& d, bool app, std::size_t n, LegacyRandom& rng) {
    Vector values;
    values.reserve(n);
    const double mu = d.mean, v = d.variance;
    const double ceiling = app ? 10. : std::numeric_limits<double>::infinity();
    const auto trunc = [&](std::size_t count, double location, double sd) {
        const TruncatedNormal distribution(location, sd, ceiling);
        for (std::size_t j = 0; j < count; ++j) values.push_back(distribution.draw(rng));
    };
    std::size_t tail_draws = n;
    if (d.name == "uniform") {
        for (std::size_t j = 0; j < n; ++j) values.push_back((app ? 10. : 2 * mu) * rng.uniform());
    } else if (d.name == "fatiguelife") {
        const double root = std::sqrt(mu * mu + 3 * v);
        const double scale = (4 * mu - root) / 3;
        const double shape = std::sqrt(2 * (root - mu) / (4 * mu - root));
        tail_draws = 0;
        for (std::size_t j = 0; j < (app ? 2 * n : n); ++j) {
            const double x = .5 * shape * rng.normal(), x2 = x * x;
            const double value = (1. + 2 * x2 + 2 * x * std::sqrt(1 + x2)) * scale;
            if (app && value > 10) continue;
            if (values.size() < n) values.push_back(value);
            ++tail_draws;
        }
        if (values.size() != n) throw std::runtime_error("APP fatigue-life retained fewer samples than requested");
    } else if (d.name == "bimodal") {
        const double sd = std::sqrt(v);
        const double p = d.component == 0 ? .6 : d.component == 1 ? .4 : .5;
        std::size_t first = 0;
        for (std::size_t j = 0; j < n; ++j) first += rng.uniform() < p;
        const double a = d.component == 0 ? mu + sd / 2 : d.component == 1 ? mu + 3 * sd / 2 : mu + sd;
        const double b = d.component == 0 ? mu - 3 * sd / 2 : d.component == 1 ? mu - sd / 2 : mu - sd;
        const double sigma = d.component <= 1 ? sd / 2 : sd / 4;
        trunc(first, a, sigma);
        trunc(n - first, b, sigma);
    } else if (d.name == "gamma") {
        const double alpha = mu * mu / v, beta = mu / (v * 1000.);
        if (!(alpha > 0 && beta > 0)) throw std::runtime_error("Invalid gamma parameters");
        for (std::size_t j = 0; j < n; ++j) values.push_back(((1 / beta) * rng.gamma(alpha)) / 1000.);
        return values;
    } else {
        trunc(n, mu, std::sqrt(v));
    }
    if (app) {
        const double first = .9, second = first + .09, third = second + .009, total = third + .001;
        for (std::size_t j = 0; j < tail_draws; ++j) {
            const double u = rng.uniform();
            if (j < n) values[j] += u < first / total ? 0 : u < second / total ? 10 : u < third / total ? 20 : 30;
        }
    }
    return values;
}

struct Row {
    Selection selection;
    double cost, probability;
    std::size_t evaluation;
};
bool by_cost_queue(const Row& a, const Row& b) {
    if (a.cost != b.cost) return a.cost < b.cost;
    return a.selection > b.selection;
}
bool by_probability_queue(const Row& a, const Row& b) {
    return std::tie(a.probability, a.cost, a.selection) > std::tie(b.probability, b.cost, b.selection);
}
Json as_json(const Row& row) {
    return {{"selection", row.selection}, {"cost", row.cost}, {"probability", row.probability}};
}
std::string csv_selection(const Selection& s) {
    return "\"" + Json(s).dump() + "\"";
}
} // namespace

double real_probability(const Instance& instance, const Selection& selection, double capacity, std::size_t draws) {
    instance.validate(selection);
    const bool app = instance.name.rfind("APP_", 0) == 0;
    if (!app && instance.name.rfind("LAB_", 0) != 0) throw std::runtime_error("Expected LAB_ or APP_ instance for real P");
    LegacyRandom rng(832273);
    Vector sums(draws);
    for (int item : selection) {
        const auto values = draw_factor(load_distribution(instance.path / (std::to_string(item) + "_dist.txt")), app, draws, rng);
        for (std::size_t i = 0; i < draws; ++i) sums[i] += values[i];
    }
    return double(std::count_if(sums.begin(), sums.end(), [&](double x) { return x <= capacity; })) / draws;
}

Json report(const Instance& instance, double capacity, std::uint32_t seed, int repetition,
            const Json& shortlist, LssEvaluator& evaluator, const fs::path& directory,
            double search_started) {
    Json trace = Json::array();
    std::size_t evaluations = 0;
    const auto evaluate = [&](const Selection& s, const char* stage) {
        const double p = evaluator.evaluate(s);
        ++evaluations;
        if (stage) trace.push_back({{"stage", stage}, {"selection", s}, {"probability", p}});
        return Row{s, instance.lss_cost(s), p, evaluations};
    };
    std::vector<Row> cost, mc, records;
    const auto push = [&](const Row& row) {
        const auto duplicate = [&](const Row& other) { return other.selection == row.selection && other.cost == row.cost; };
        if (std::none_of(mc.begin(), mc.end(), duplicate)) {
            mc.push_back(row);
            if (mc.size() > 30) {
                std::stable_sort(mc.begin(), mc.end(), [](const Row& a, const Row& b) {
                    if (a.probability != b.probability) return a.probability > b.probability;
                    return a.cost < b.cost;
                });
                mc.pop_back();
            }
        }
        if (std::none_of(cost.begin(), cost.end(), duplicate)) {
            cost.push_back(row);
            std::sort(cost.begin(), cost.end(), by_cost_queue);
            if (cost.size() > 30) cost.pop_back();
        }
    };
    for (const auto& candidate : shortlist) {
        const auto row = evaluate(candidate.at("selection").get<Selection>(), "S10_result_to_LSS_initial");
        if (row.probability >= .99) { push(row); records.push_back(row); break; }
    }
    if (records.empty()) {
        write_json(directory / "ORIGINAL_LSS_DECISION_TRACE.json", trace);
        throw std::runtime_error("No S10-generated candidate passes original LSS decision");
    }
    for (const auto& candidate : shortlist) {
        const auto row = evaluate(candidate.at("selection").get<Selection>(), "S10_pool_original_LSS_decision");
        if (row.probability >= .99) { push(row); records.push_back(row); }
    }
    for (auto& row : cost) {
        evaluate(row.selection, nullptr);
        row.probability = evaluate(row.selection, nullptr).probability;
    }
    std::sort(mc.begin(), mc.end(), by_probability_queue);
    // The frozen Python update writes the recheck result into Mlist[i], where
    // i is the final index of the preceding cost loop. Preserve that behavior.
    for (std::size_t j = 0; j < mc.size(); ++j) {
        evaluate(mc[j].selection, nullptr);
        mc.at(cost.size() - 1).probability = evaluate(mc[j].selection, nullptr).probability;
    }
    std::sort(mc.begin(), mc.end(), by_probability_queue);
    Row second = cost.front();
    for (const auto& row : cost) {
        if (row.probability >= second.probability) second = row;
        if (row.probability >= .995) break;
    }
    std::map<Selection, std::pair<double, Row>> ranking;
    for (std::size_t i = 0; i < cost.size(); ++i) ranking[cost[i].selection] = {.7 * (30 - i), cost[i]};
    for (std::size_t i = 0; i < mc.size(); ++i) {
        auto& [score, row] = ranking[mc[i].selection];
        score += (1 - .7) * (30 - i);
        row = mc[i];
    }
    const auto rank = [](const auto& a) {
        const auto& [score, row] = a.second;
        return std::make_tuple(score, row.cost, row.probability, row.selection);
    };
    const auto weighted = std::max_element(ranking.begin(), ranking.end(),
        [&](const auto& a, const auto& b) { return rank(a) < rank(b); })->second.second;
    const double elapsed = now() - search_started;
    const auto output = directory / "result" / "Localsearch";
    fs::create_directories(output);
    std::string name = instance.name;
    for (char& ch : name) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    std::ostringstream threshold;
    threshold << std::setprecision(15) << capacity;
    const std::string stem = "LocalSearch_" + name + threshold.str();
    const auto csv = [&](const std::string& suffix, const char* header) {
        std::ofstream file(output / (stem + suffix + ".csv"), std::ios::binary);
        if (!file) throw std::runtime_error("Cannot create LSS CSV");
        file << std::setprecision(17) << header << "\r\n";
        return file;
    };
    std::map<Selection, double> truth;
    const auto real = [&](const Selection& s) {
        auto [it, fresh] = truth.try_emplace(s);
        if (fresh) it->second = real_probability(instance, s, capacity);
        return it->second;
    };
    Json variants = Json::array();
    const Row outputs[] = {cost.front(), second, weighted};
    for (int i = 0; i < 3; ++i) {
        const auto& row = outputs[i];
        const double real_p = real(row.selection);
        auto file = csv("_" + std::to_string(i), "Times,Cost,Confidence Level,Evaluation Times,Solution,Real Confidence Level,Running Time");
        file << repetition - 1 << ',' << row.cost << ',' << row.probability << ',' << evaluations << ','
             << csv_selection(row.selection) << ',' << real_p << ',' << elapsed << "\r\n";
        auto variant = as_json(row);
        variant["real_probability"] = real_p;
        variants.push_back(variant);
    }
    auto top = csv("_3", "Cost,Confidence Level,Solution,Real Confidence Level,Running Time");
    auto record = csv("_record", "Times,Cost,Confidence Level,Solution");
    if (repetition == 1) {
        for (std::size_t i = 0; i < std::min<std::size_t>(10, cost.size()); ++i) {
            const auto& row = cost[i];
            top << row.cost << ',' << row.probability << ',' << csv_selection(row.selection) << ','
                << real(row.selection) << ',' << elapsed << "\r\n";
        }
        for (const auto& row : records)
            record << row.evaluation << ',' << row.cost << ',' << row.probability << ',' << csv_selection(row.selection) << "\r\n";
    }
    write_json(directory / "ORIGINAL_LSS_DECISION_TRACE.json", trace);
    const auto& main = variants[0];
    return {{"status", "completed"}, {"instance", instance.name}, {"capacity", capacity},
        {"search_seed", seed}, {"rep", repetition}, {"cost", main["cost"]}, {"selection", main["selection"]},
        {"original_LSS_confidence", main["probability"]}, {"recorded_real_probability", main["real_probability"]},
        {"original_mainflow_search_seconds", elapsed}, {"original_output_variants", variants},
        {"evaluation_times", evaluations}};
}
} // namespace s10
