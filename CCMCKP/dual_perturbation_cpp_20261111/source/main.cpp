#include "search.hpp"

#include <atomic>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <thread>

namespace {
using namespace ccmckp;
namespace fs = std::filesystem;

struct Arguments {
    fs::path instance, output = "result/dual_cpp", cache = ".cache/ddts_reference_quick_check";
    std::vector<double> tmax;
    Settings settings;
    double lambda = 5, quick_seconds = 1;
    int runs = 1, workers = 1;
    bool trace = false, inspect = false;
    std::uint64_t eval_budget = 0;
};

void usage() {
    std::cout << "ccmckp_dual --instance DIR --tmax T [T ...]\n"
        "  --p0 P --lambda-value L --seed N --runs N --run-workers N\n"
        "  --mc-samples N --init-pilot-samples N --init-validation-samples N\n"
        "  --tabu-tenure N --quick-check-timeout SEC --quick-check-cache-dir DIR\n"
        "  --output-dir DIR --trace --inspect\n"
        "  Normal run: 600 s. --evaluation-budget N is for parity diagnostics.\n";
}

int positive(const std::string& value) {
    std::size_t end = 0;
    const int parsed = std::stoi(value, &end);
    if (end != value.size() || parsed <= 0) throw std::invalid_argument("expected positive integer: " + value);
    return parsed;
}

std::uint64_t unsigned_value(const std::string& value) {
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos) {
        throw std::invalid_argument("expected non-negative integer: " + value);
    }
    return std::stoull(value);
}

double real(const std::string& value) {
    std::size_t end = 0;
    const double parsed = std::stod(value, &end);
    if (end != value.size() || !std::isfinite(parsed)) throw std::invalid_argument("invalid number: " + value);
    return parsed;
}

Arguments arguments(int argc, char** argv) {
    Arguments args;
    for (int i = 1; i < argc; ++i) {
        const std::string option = argv[i];
        const auto next = [&]() {
            if (i + 1 == argc) throw std::invalid_argument("missing value for " + option);
            return std::string(argv[++i]);
        };
        if (option == "--instance") args.instance = fs::u8path(next());
        else if (option == "--output-dir") args.output = fs::u8path(next());
        else if (option == "--quick-check-cache-dir") args.cache = fs::u8path(next());
        else if (option == "--tmax") {
            args.tmax.push_back(real(next()));
            while (i + 1 < argc && std::string(argv[i + 1]).rfind("--", 0) != 0) {
                args.tmax.push_back(real(next()));
            }
        } else if (option == "--p0") args.settings.p0 = real(next());
        else if (option == "--lambda-value") args.lambda = real(next());
        else if (option == "--quick-check-timeout") args.quick_seconds = std::max(0.0, real(next()));
        else if (option == "--mc-samples") args.settings.mc_samples = positive(next());
        else if (option == "--init-pilot-samples") args.settings.pilot_samples = positive(next());
        else if (option == "--init-validation-samples") args.settings.validation_samples = positive(next());
        else if (option == "--tabu-tenure") args.settings.tabu_tenure = positive(next());
        else if (option == "--seed") {
            const auto seed = unsigned_value(next());
            if (seed > UINT32_MAX) throw std::invalid_argument("seed exceeds uint32 range");
            args.settings.seed = static_cast<std::uint32_t>(seed);
        } else if (option == "--runs") args.runs = positive(next());
        else if (option == "--run-workers") args.workers = positive(next());
        else if (option == "--time-limit") {
            if (real(next()) != 600) throw std::invalid_argument("the original time limit is 600 seconds");
        } else if (option == "--evaluation-budget") args.eval_budget = unsigned_value(next());
        else if (option == "--trace") args.trace = true;
        else if (option == "--inspect") args.inspect = true;
        else throw std::invalid_argument("unknown option " + option);
    }
    if (args.instance.empty() || args.tmax.empty()) throw std::invalid_argument("--instance and --tmax are required");
    if (!fs::is_directory(args.instance)) args.instance = fs::path("benchmark") / args.instance;
    if (!(0 < args.settings.p0 && args.settings.p0 < 1)) throw std::invalid_argument("require 0 < p0 < 1");
    if (args.settings.validation_samples <= args.settings.pilot_samples) {
        throw std::invalid_argument("require 0 < pilot_samples < validation_samples");
    }
    if (std::uint64_t(args.settings.seed) + args.runs - 1 > UINT32_MAX) {
        throw std::invalid_argument("last run seed exceeds uint32 range");
    }
    return args;
}

std::string formatted(double value) {
    std::ostringstream out;
    out << value;
    return out.str();
}

std::ofstream file(const fs::path& path) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write " + path.string());
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out << std::setprecision(17);
    return out;
}

void write_result(const fs::path& path, const Instance& instance, const Settings& settings, const Result& r) {
    auto out = file(path);
    out << "{\n  \"instance\":" << std::quoted(instance.name)
        << ",\n  \"Tmax\":" << settings.tmax << ",\n  \"P0\":" << settings.p0
        << ",\n  \"time_limit_seconds\":600"
        << ",\n  \"mc_sample_size\":" << settings.mc_samples
        << ",\n  \"probability_evaluator\":\""
        << (instance.exact() ? "author_reference_exact" : "author_reference_advanced_monte_carlo") << "\""
        << ",\n  \"seed\":" << settings.seed << ",\n  \"cost\":" << r.cost
        << ",\n  \"probability\":" << r.probability << ",\n  \"certified_feasible\":true"
        << ",\n  \"solution\":";
    write_selection(out, r.solution);
    out << ",\n  \"initial_solution\":";
    write_selection(out, r.initial_solution);
    out << ",\n  \"initial_cost\":" << r.initial_cost << ",\n  \"initial_probability\":" << r.initial_probability
        << ",\n  \"initialization_source\":\"" << r.initialization << "\""
        << ",\n  \"initialization_repair_count\":" << r.init_repairs
        << ",\n  \"evaluation_count\":" << r.evaluations << ",\n  \"completed_cycles\":" << r.cycles
        << ",\n  \"total_class_scans\":" << r.class_scans << ",\n  \"total_tabu_moves\":" << r.tabu_moves
        << ",\n  \"perturbation_count\":" << r.perturbations
        << ",\n  \"dual_perturbation_enabled\":true"
        << ",\n  \"strong_perturbation_count\":" << r.strong_perturbations
        << ",\n  \"strong_destroyed_class_count\":" << r.strong_destroyed_classes
        << ",\n  \"strong_perturb_no_improve\":" << strong_no_improve
        << ",\n  \"strong_perturb_class_ratio\":" << strong_class_ratio
        << ",\n  \"pair_exchange_count\":" << r.pair_exchanges
        << ",\n  \"pair_exchange_evaluation_count\":" << r.pair_evaluations
        << ",\n  \"pair_exchange_proposal_count\":" << r.pair_proposals
        << ",\n  \"reactive_repeat_count\":" << r.repeats
        << ",\n  \"reactive_maximum_tenure\":" << r.maximum_tenure
        << ",\n  \"reactive_tenure_updates\":" << r.tenure_updates
        << ",\n  \"best_found_time_seconds\":" << r.best_found_seconds
        << ",\n  \"total_runtime_seconds\":" << r.seconds
        << ",\n  \"stop_reason\":\"" << r.stop_reason << "\"\n}\n";
}

void inspect_data(const fs::path& path, const Instance& instance, const Groups& rows, bool timed_out) {
    auto out = file(path);
    out << "{\n  \"exact\":" << std::boolalpha << instance.exact()
        << ",\n  \"quick_check_timed_out\":" << timed_out;
    for (const auto& [label, groups] : std::initializer_list<std::pair<const char*, const Groups*>>{
             {"weight", &instance.weight}, {"utility", &instance.utility},
             {"value", &instance.value}, {"quick_check_list", &rows}}) {
        out << ",\n  \"" << label << "\":[";
        for (std::size_t i = 0; i < groups->size(); ++i) {
            if (i) out << ',';
            write_selection(out, (*groups)[i]);
        }
        out << ']';
    }
    out << "\n}\n";
}

bool run_all(const Arguments& args, const Instance& instance, const Groups& rows, std::ostream& summary) {
    bool success = true;
    for (double tmax : args.tmax) {
        const std::string stem = instance.name + "_T" + formatted(tmax) + "_p" + formatted(args.settings.p0);
        std::vector<Result> results(args.runs);
        std::vector<std::string> errors(args.runs);
        std::atomic<int> next{0};
        const auto worker = [&] {
            for (int r = next.fetch_add(1); r < args.runs; r = next.fetch_add(1)) {
                auto settings = args.settings;
                settings.tmax = tmax;
                settings.seed += r;
                const auto run_name = stem + "_run" + std::to_string(r);
                try {
                    std::ofstream trace;
                    if (args.trace) trace = file(args.output / (run_name + "_trace.csv"));
                    auto result = solve(instance, settings, rows, args.trace ? &trace : nullptr, args.eval_budget);
                    write_result(args.output / (run_name + ".json"), instance, settings, result);
                    results[r] = std::move(result);
                } catch (const std::exception& error) {
                    errors[r] = error.what();
                }
            }
        };
        std::vector<std::thread> workers;
        try {
            for (int i = 1; i < std::min(args.runs, args.workers); ++i) workers.emplace_back(worker);
            worker();
        } catch (...) {
            for (auto& thread : workers) thread.join();
            throw;
        }
        for (auto& thread : workers) thread.join();

        std::vector<const Result*> feasible;
        double best = std::numeric_limits<double>::infinity();
        long double total = 0, runtime = 0;
        for (int r = 0; r < args.runs; ++r) {
            if (!errors[r].empty()) {
                std::cerr << stem << " run " << r << " failed: " << errors[r] << '\n';
                success = false;
                continue;
            }
            const auto& result = results[r];
            feasible.push_back(&result);
            best = std::min(best, result.cost);
            total += result.cost;
            runtime += result.seconds;
            std::cout << std::setprecision(12) << stem << " run " << r << " cost=" << result.cost
                << " p=" << result.probability << " evaluations=" << result.evaluations << '\n';
        }
        summary << instance.name << ',' << tmax << ',' << args.settings.p0 << ','
                << args.runs << ',' << feasible.size() << ','
                << static_cast<double>(feasible.size()) / args.runs << ',';
        if (!feasible.empty()) {
            const auto avg = total / feasible.size();
            long double squared = 0, best_time = 0;
            std::size_t best_count = 0;
            const auto best_tol = std::max(1e-9, std::abs(best) * 1e-10);
            for (const auto* result : feasible) {
                const auto delta = result->cost - avg;
                squared += delta * delta;
                if (std::abs(result->cost - best) <= best_tol) {
                    best_time += result->best_found_seconds;
                    ++best_count;
                }
            }
            const auto stdev = std::sqrt(squared / feasible.size());
            summary << best << ',' << avg << ',' << stdev << ','
                    << best_time / best_count << ',' << runtime / feasible.size();
        } else {
            summary << ",,,,";
        }
        summary << '\n';
        summary.flush();
    }
    return success;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 1 || (argc == 2 && std::string(argv[1]) == "--help")) {
            usage();
            return argc == 1 ? 2 : 0;
        }
        const auto args = arguments(argc, argv);
        const auto instance = ccmckp::read_instance(args.instance, args.lambda);
        fs::create_directories(args.output);
        bool timed_out;
        const auto rows = ccmckp::quick_check(instance, args.settings.p0, args.quick_seconds, args.cache, timed_out);
        if (args.inspect) inspect_data(args.output / "instance_resources.json", instance, rows, timed_out);
        auto summary = file(args.output / "ddts_summary.csv");
        summary << "instance,Tmax,P0,runs,feasible_runs,feasibility_rate,best_cost,mean_cost,std_cost,"
                   "mean_time_to_best_for_best_runs,mean_total_runtime_seconds\n";
        return run_all(args, instance, rows, summary) ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "ccmckp_dual: " << error.what() << '\n';
        return 2;
    }
}
