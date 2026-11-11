#include "report.hpp"
#include "search.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <sstream>

namespace {
using namespace s10;

void usage() {
    std::cout <<
        "ccmckp_s10 --instance DIR --capacity T --seed N --out NEW_DIR [--rep N]\n"
        "ccmckp_s10 --index 1..40 --rep 1..30 --benchmark-root DIR --out NEW_DIR\n"
        "Options: --seconds 600 --backend gurobi|highs --local-phases none|pre|post|both\n"
        "         --search-only [--cases CASES.json] [--manifest BENCHMARK_MANIFEST.json]\n"
        "Evaluation: --instance DIR --capacity T --seed N --evaluate ID,ID,...\n"
        "            [--bins 4096] [--real] [--draws N] [--lss-repeats N]\n";
}

unsigned long long natural(const std::string& text) {
    std::size_t used = 0;
    const auto value = std::stoull(text, &used);
    if (used != text.size() || text.empty() || text[0] == '-') throw std::runtime_error("Invalid integer " + text);
    return value;
}

double number(const std::string& text) {
    std::size_t used = 0;
    const auto value = std::stod(text, &used);
    if (used != text.size() || !std::isfinite(value)) throw std::runtime_error("Invalid number " + text);
    return value;
}

Selection selection(const std::string& text) {
    Selection result;
    std::istringstream in(text);
    for (std::string s; std::getline(in, s, ',');) {
        const auto id = natural(s);
        if (id > std::numeric_limits<int>::max()) throw std::runtime_error("Invalid item ID");
        result.push_back(static_cast<int>(id));
    }
    return result;
}

Json verify_inputs(const Instance& instance, const fs::path& manifest) {
    Json hashes = Json::object();
    const auto record = [&](const std::string& name) { hashes[name] = sha256(instance.path / name); };
    record("cost.txt");
    record("node_to_factor.pkl");
    for (int i = 0; i < instance.n(); ++i) record(std::to_string(i) + "_sample.txt");
    if (!manifest.empty()) {
        const auto baseline = read_json(manifest).at(instance.name);
        for (const auto& [file, hash] : hashes.items())
            if (baseline.at(file) != hash) throw std::runtime_error("Frozen input SHA256 mismatch: " + file);
    }
    return hashes;
}
} // namespace

int main(int argc, char** argv) {
    using namespace s10;
    fs::path failure_dir;
    try {
        std::map<std::string, std::string> args;
        std::set<std::string> flags;
        const std::set<std::string> keys{"instance", "capacity", "seed", "out", "index", "rep", "benchmark-root",
            "seconds", "backend", "local-phases", "cases", "manifest", "evaluate", "bins", "draws", "lss-repeats"};
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") { usage(); return 0; }
            if (option == "--search-only" || option == "--real") { flags.insert(option); continue; }
            if (option.rfind("--", 0) != 0 || !keys.count(option.substr(2)) || i + 1 == argc)
                throw std::runtime_error("Unknown or incomplete option " + option);
            if (!args.emplace(option.substr(2), argv[i + 1]).second)
                throw std::runtime_error("Duplicate option " + option);
            ++i;
        }
        const auto arg = [&](const std::string& key, const std::string& default_value = "") {
            auto it = args.find(key);
            return it == args.end() ? default_value : it->second;
        };
        const auto rep = natural(arg("rep", "1"));
        if (rep < 1 || rep > 30) throw std::runtime_error("rep must be 1..30");
        fs::path path = fs::u8path(arg("instance")), manifest = fs::u8path(arg("manifest"));
        std::string cap = arg("capacity"), seed_arg = arg("seed");
        const auto backend = arg("backend", "gurobi"), local = arg("local-phases", "none");
        if (backend != "gurobi" && backend != "highs") throw std::runtime_error("Invalid backend");
        if (local != "none" && local != "pre" && local != "post" && local != "both")
            throw std::runtime_error("Invalid local phase option");
        const auto seconds = number(arg("seconds", "600"));
        if (seconds < 30 || seconds > 600) throw std::runtime_error("seconds must be 30..600");

        unsigned long long index = 0;
        if (args.count("index")) {
            if (!path.empty() || !cap.empty() || !seed_arg.empty() || arg("benchmark-root").empty())
                throw std::runtime_error("Use --index with --benchmark-root, or use explicit instance, capacity and seed");
            index = natural(arg("index"));
            if (index < 1 || index > 40) throw std::runtime_error("index must be 1..40");
            auto directory = fs::absolute(fs::u8path(argv[0])).parent_path();
            const auto cases = read_json(fs::u8path(arg("cases", (directory / "CASES.json").u8string())));
            const auto found = std::find_if(cases.begin(), cases.end(), [&](const Json& c) { return c.at("index") == index; });
            if (found == cases.end()) throw std::runtime_error("Case index missing");
            path = fs::u8path(arg("benchmark-root")) / found->at("instance").get<std::string>();
            cap = found->at("tmax").dump();
            seed_arg = std::to_string(960000 + rep);
            if (manifest.empty()) manifest = directory / "BENCHMARK_MANIFEST.json";
        }
        if (path.empty() || cap.empty() || seed_arg.empty()) { usage(); return 2; }
        const double capacity = number(cap);
        if (capacity <= 0) throw std::runtime_error("Capacity must be positive");
        cap = Json(capacity).dump(); // Match Fraction(str(parsed_float)) in the frozen runner.
        const auto seed_number = natural(seed_arg);
        if (seed_number > std::numeric_limits<int>::max() ||
            (backend == "gurobi" && seed_number > 2000000000ULL))
            throw std::runtime_error("Seed exceeds the backend's supported range");
        const auto seed = static_cast<std::uint32_t>(seed_number);

        if (args.count("evaluate")) {
            Instance instance(path);
            const auto s = selection(arg("evaluate"));
            instance.validate(s);
            const auto bins = natural(arg("bins", "4096"));
            if (bins < 2 || bins > 1048576) throw std::runtime_error("bins must be 2..1048576");
            const auto draws = natural(arg("draws", "1000000"));
            const auto repeats = natural(arg("lss-repeats", "1"));
            if (!draws || !repeats) throw std::runtime_error("Draw and repetition counts must be positive");
            LssEvaluator lss(instance, capacity, seed, draws);
            ExactOracle oracle(instance, cap);
            Search probe(instance, {capacity, cap, seed, seconds, backend, local, {}}, now());
            const auto& idx = probe.screen_indices();
            const auto preview_end = idx.begin() + std::min<std::size_t>(64, idx.size());
            Json samples = Json::array();
            for (unsigned long long i = 0; i < repeats; ++i) samples.push_back(lss.evaluate(s));
            Json out = {{"grid", oracle.certify(s, static_cast<int>(bins)).json(s)},
                        {"lss", samples}, {"lss_quick", lss.quick_checks()}, {"native_quick", probe.quick_checks()},
                        {"pcg_int16_first_64", std::vector<std::uint16_t>(idx.begin(), preview_end)}};
            if (instance.m() <= 5)
                out["small"] = SmallCounts(instance, capacity).count(s).json(s);
            if (flags.count("--real")) out["real_probability"] = real_probability(
                instance, s, capacity, args.count("draws") ? draws : 10000000);
            std::cout << out.dump() << '\n';
            return 0;
        }

        const auto output = fs::u8path(arg("out"));
        if (output.empty() || fs::exists(output)) throw std::runtime_error("--out must be a new directory");
        if (!fs::create_directories(output)) throw std::runtime_error("Cannot reserve output directory");
        failure_dir = output;

        const double load_started = now();
        Instance instance(path);
        const double load_seconds = now() - load_started;
        const auto input_hashes = verify_inputs(instance, manifest);
        std::optional<LssEvaluator> lss;
        if (!flags.count("--search-only")) lss.emplace(instance, capacity, seed);
        const double search_started = now();
        const double started = search_started - load_seconds;
        Search search(instance, {capacity, cap, seed, seconds, backend, local, output / "S10_search.json"}, started);
        const auto raw = search.run();
        const double elapsed = now() - started;
        Json metadata = {{"schema", "S10_raw_constraint_portfolio_worker"}, {"elapsed", elapsed},
            {"within_budget", elapsed <= seconds}, {"selected", raw.at("selected")},
            {"seed", seed}, {"budget", seconds}, {"backend", backend}, {"local_phases", local},
            {"phase_records", search.phase_records}, {"input_sha256", input_hashes}};
        write_json(output / "S10_search.run.json", metadata);

        if (!metadata.at("within_budget").get<bool>()) throw std::runtime_error("S10 search exceeded its wall-clock budget");
        if (lss) {
            const double report_validation_start = now();
            if (!manifest.empty()) {
                const auto registered = read_json(manifest).at(instance.name);
                for (int j = 0; j < instance.n(); ++j) {
                    const auto file = std::to_string(j) + "_dist.txt";
                    if (registered.at(file) != sha256(instance.path / file))
                        throw std::runtime_error("Frozen reporting input SHA256 mismatch: " + file);
                }
            }
            auto result = report(instance, capacity, seed, static_cast<int>(rep), raw.at("candidate_shortlist"),
                                 *lss, output, search_started + (now() - report_validation_start));
            result["backend"] = backend;
            result["local_phases"] = local;
            result["arm"] = backend == "gurobi" && local == "none" ? "G_NONE" : backend + "_" + local;
            if (index) result["case_index"] = index;
            result["phase_records"] = search.phase_records;
            result["raw_best_cost"] = raw.at("selected").at("cost");
            result["S10_worker_search_seconds"] = elapsed;
            result["S10_candidates"] = raw.at("candidate_shortlist").size();
            result["S10_exhaustive"] = raw.at("exhaustive");
            result["wall_seconds_including_original_realP_reporting"] = now() - started;
            write_json(output / "RESULT.json", result);
            std::cout << result.dump() << '\n';
        } else std::cout << metadata.dump() << '\n';
        return 0;
    } catch (const std::exception& error) {
        if (!failure_dir.empty()) {
            try { write_json(failure_dir / "FAILED.json", {{"status", "failed"}, {"error", error.what()}}); }
            catch (...) {}
        }
        std::cerr << "S10: " << error.what() << '\n';
        return 1;
    }
}
