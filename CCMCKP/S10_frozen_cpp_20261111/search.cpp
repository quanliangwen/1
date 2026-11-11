#include "search.hpp"
#include "fft.hpp"
#include "partition.hpp"
#include "third_party/picosha2.h"
#include <array>
#include <cmath>
#include <numeric>
#include <tuple>

namespace s10 {
namespace {
constexpr double inf = std::numeric_limits<double>::infinity();
constexpr int guide_bins = 16384;

template <class T> std::vector<T> impulse(int bins) {
    std::vector<T> h(bins);
    h[0] = 1;
    return h;
}
template <class T> std::vector<T> reverse_cdf(const std::vector<T>& pdf) {
    std::vector<T> result(pdf.size());
    std::partial_sum(pdf.begin(), pdf.end(), result.rbegin());
    return result;
}
Vector negated(Vector values) {
    for (double& v : values) v = -v;
    return values;
}
Vector weights(int bins) {
    Vector result(bins);
    for (int i = 0; i < bins; ++i) result[i] = std::exp(-16. * i / bins);
    return result;
}
Freq<double> weighted_transform(Vector histogram, const Vector& weight) {
    for (std::size_t i = 0; i < weight.size(); ++i) histogram[i] *= weight[i];
    return forward(histogram);
}
double unweighted_sum(const Freq<double>& freq, const Vector& weight) {
    auto pdf = inverse(freq, false);
    for (std::size_t i = 0; i < pdf.size(); ++i) pdf[i] /= weight[i];
    return sum(pdf);
}
template <class T>
T dot(const std::vector<T>& a, const std::vector<T>& b) {
    return std::inner_product(a.begin(), a.end(), b.begin(), T(0));
}

std::string hash_text(const picosha2::hash256_one_by_one& hash) {
    std::vector<unsigned char> digest(32);
    hash.get_hash_bytes(digest.begin(), digest.end());
    return picosha2::bytes_to_hex_string(digest.begin(), digest.end());
}
std::string join(const Selection& values) {
    std::string result;
    for (int v : values) {
        if (!result.empty()) result += ',';
        result += std::to_string(v);
    }
    return result;
}
} // namespace

Search::Search(const Instance& instance, Options options, double started)
    : instance(instance), options(std::move(options)), started(started),
      deadline(started + this->options.seconds - std::min(45., this->options.seconds * .12)),
      oracle(instance, this->options.capacity_text), model(instance, this->options.backend, this->options.seed),
      checks(native_checks(instance.sample_count, instance.m())) {
    ccmckp::Pcg64 rng(this->options.seed);
    indices = rng.integers16(static_cast<std::uint16_t>(instance.sample_count - 1), std::size_t(instance.m()) * 60000);
}

Json Search::Candidate::json() const {
    return {{"selection", selection}, {"cost", cost}, {"certificate", certificate.json(selection)},
            {"source", source}, {"found_seconds", found_seconds}};
}

Groups Search::binary(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int count) {
    if (remaining() < 5) return {};
    const double begin = now();
    auto out = model.solve(objective, rows, std::min(seconds, remaining() - 3), count);
    ++models;
    model_seconds += now() - begin;
    return out;
}

Groups Search::mip(const Vector& weights, double rhs, std::optional<double> vcap,
                   int trust, const Selection& center, double seconds, int count) {
    std::vector<LinearRow> rows;
    if (best) rows.push_back({instance.costs, -inf, best->cost - 1e-7});
    rows.push_back({weights, -inf, rhs});
    if (vcap) rows.push_back({instance.variance, -inf, *vcap});
    if (!center.empty()) {
        Vector row(instance.n());
        for (int j : center) row[j] = 1;
        rows.push_back({std::move(row), double(instance.m() - trust), inf});
    }
    return binary(instance.costs, rows, seconds, count);
}

Selection Search::minimum(const Vector& objective) const {
    Selection s;
    for (const auto& g : instance.groups)
        s.push_back(*std::min_element(g.begin(), g.end(), [&](int a, int b) { return objective[a] < objective[b]; }));
    return s;
}

Groups Search::cost_order(const std::set<Selection>& selections) const {
    std::vector<std::pair<double, Selection>> keyed;
    for (const auto& s : selections) keyed.emplace_back(instance.cost_of(s), s);
    std::sort(keyed.begin(), keyed.end());
    Groups result;
    for (auto& entry : keyed) result.push_back(std::move(entry.second));
    return result;
}

double Search::accept(const Selection& s, std::string source, const Certificate& c) {
    if (!c.accepted()) throw std::logic_error("Raw .99 certificate required");
    Candidate record{s, instance.cost_of(s), c, std::move(source), now() - started};
    const double p = c.probability();
    pool.insert_or_assign(s, record);
    decisions[s] = p;
    if (!best || record.cost < best->cost - 1e-8) {
        best = record;
        events.push_back({{"event", "raw_certified_incumbent"}, {"cost", record.cost},
                          {"elapsed", record.found_seconds}, {"source", record.source}});
        if (now() - last_save > 10) save("running");
    }
    return p;
}

std::pair<double, double> Search::float_bounds(const Selection& selection, int bins) {
    const auto weight = weights(bins);
    double bounds[2] = {};
    for (int i = 0; i < 2; ++i) {
        Freq<double> freq(bins + 1, 1);
        for (int j : selection) {
            const auto& indices = oracle.quantized(j, bins, i == 0);
            Vector h(bins);
            for (int k : indices) if (k < bins) h[k] += 1;
            for (double& v : h) v /= indices.size();
            multiply(freq, weighted_transform(std::move(h), weight));
        }
        bounds[i] = unweighted_sum(freq, weight);
    }
    return {bounds[0], bounds[1]};
}

double Search::native_check(const Selection& s, const std::string& source) {
    instance.validate(s);
    if (auto it = pool.find(s); it != pool.end()) return it->second.certificate.probability();
    if (remaining() < 5) return 0;
    if (auto it = decisions.find(s); it != decisions.end()) return it->second;
    for (int bins : {1024, 4096, 16384, 65536, 262144, 1048576}) {
        if (remaining() < 5 || (bins >= 262144 && remaining() < 45)) break;
        const auto [lo, hi] = float_bounds(s, bins);
        if (hi < .99 - 1e-7 || lo >= .99 + 1e-8 || bins >= 262144) {
            const auto c = oracle.certify(s, bins);
            if (c.infeasible()) return decisions[s] = c.probability();
            if (c.accepted() && (lo >= .99 + 1e-8 || bins >= 262144)) return accept(s, source, c);
        }
    }
    return decisions[s] = 0;
}

void Search::small_exact_search() {
    std::set<Selection> choices;
    Selection s(instance.m());
    const auto enumerate = [&](const auto& self, int g) -> void {
        if (g == instance.m()) { choices.insert(s); return; }
        for (int j : instance.groups[g]) {
            s[g] = j;
            self(self, g + 1);
        }
    };
    enumerate(enumerate, 0);
    SmallCounts counter(instance, options.capacity);
    picosha2::hash256_one_by_one digest;
    std::size_t checked = 0, refuted = 0, ambiguous = 0;
    for (const auto& q : cost_order(choices)) {
        if (remaining() < 55) break;
        const auto c = counter.count(q);
        const auto encoded = Json::array({q, c.lower.get_str(), c.upper.get_str()}).dump();
        digest.process(encoded.begin(), encoded.end());
        ++checked;
        if (c.accepted()) accept(q, "cost_ordered_raw_enumeration", c);
        else if (c.infeasible()) ++refuted;
        else {
            ++ambiguous;
            native_check(q, "interval_boundary_refinement");
        }
    }
    digest.finish();
    exhaustive = {{"total", choices.size()}, {"checked", checked}, {"complete", checked == choices.size()},
                  {"refuted", refuted}, {"ambiguous", ambiguous}, {"counts_sha256", hash_text(digest)},
                  {"raw_feasible_found", pool.size()}, {"no_tail_gate", true}};
}

void Search::init_frontier() {
    const auto minmu = minimum(instance.mean), mincost = minimum(instance.costs);
    const auto variance = [&](const Selection& s) {
        Vector terms;
        for (int j : s) terms.push_back(instance.variance[j]);
        return sum(terms);
    };
    const double v0 = std::max(1e-9, variance(minmu)), v1 = std::max(2 * v0, variance(mincost));
    frontier_candidates = {minmu, mincost};
    for (int i = 0; i < 20 && remaining() >= 20; ++i) {
        const double v = i == 0 ? v0 * .5 : i == 19 ? v1 * 1.5 :
            std::pow(10., std::log10(v0 * .5) + (std::log10(v1 * 1.5) - std::log10(v0 * .5)) / 19 * i);
        const auto proposals = mip(instance.mean, options.capacity - 2.4 * std::sqrt(v), v, 0, {}, 2, 4);
        frontier_candidates.insert(proposals.begin(), proposals.end());
    }
    for (const auto& s : cost_order(frontier_candidates)) native_check(s, "independent_mean_variance_frontier");
    Vector low_risk = instance.mean;
    for (int j = 0; j < instance.n(); ++j) low_risk[j] += 3 * instance.sd[j];
    if (!best) {
        const double max_cost = *std::max_element(instance.costs.begin(), instance.costs.end());
        auto proposals = binary(low_risk, {{instance.costs, -inf, max_cost * instance.m()}}, 3, 8);
        const auto score = [&](const Selection& s) {
            Vector values;
            for (int j : s) values.push_back(low_risk[j]);
            return std::make_tuple(sum(values), instance.cost_of(s), s);
        };
        std::sort(proposals.begin(), proposals.end(), [&](const auto& a, const auto& b) { return score(a) < score(b); });
        for (const auto& s : proposals) {
            native_check(s, "original_low_risk_fallback");
            if (best) break;
        }
    }
    const double end = std::min(deadline - 20, now() + std::min(100., options.seconds * .2));
    auto center = minimum(low_risk);
    native_check(center, "raw_sample_low_risk_anchor");
    for (double level : {.9999, .999, .997, .995, .993, .992, .991, .9901}) {
        if (now() > end) break;
        for (int i = 0; i < 2 && now() <= end; ++i) {
            auto [p, w] = gradients(center);
            auto incumbent = std::move(best);
            best.reset();
            const auto proposals = mip(negated(w), p - level, {}, std::min(16, instance.m()), center, .7, 4);
            best = std::move(incumbent);
            for (const auto& q : proposals) {
                if (now() > end) break;
                native_check(q, "unconstrained_cost_risk_portfolio");
            }
            const Candidate* eligible = nullptr;
            // The original visits all accepted records here and caches their CDF scores.
            for (const auto& [s, record] : pool)
                if (guide_probability(s) >= level &&
                    (!eligible || std::tie(record.cost, s) < std::tie(eligible->cost, eligible->selection)))
                    eligible = &record;
            if (eligible) center = eligible->selection;
        }
    }
}

std::vector<Vector> Search::histograms(int bins, double delta) const {
    std::vector<Vector> result;
    for (const auto& samples : instance.samples) {
        Vector h(bins);
        int top = 0;
        for (double x : samples) {
            const double scaled = std::nearbyint(x / options.capacity * bins);
            const int idx = scaled >= bins ? bins : static_cast<int>(scaled);
            if (idx < bins) h[idx] += 1;
            top = std::max(top, idx);
        }
        for (double& v : h) v /= samples.size();
        double left = delta;
        for (double& v : h) {
            if (v == 0) continue;
            const double moved = std::min(left, v);
            v -= moved;
            left -= moved;
            if (left <= 1e-15) break;
        }
        if (top < bins) h[top] += delta - left;
        result.push_back(std::move(h));
    }
    return result;
}

std::pair<double, Vector> Search::gradients(const Selection& s) {
    if (guide_hist.empty()) guide_hist = histograms(guide_bins, 0);
    const int m = instance.m();
    std::vector<Vector> pref{impulse<double>(guide_bins)}, suff(m + 1);
    suff[m] = pref.front();
    for (int j : s) pref.push_back(convolve(pref.back(), guide_hist[j]));
    for (int g = m - 1; g >= 0; --g) suff[g] = convolve(guide_hist[s[g]], suff[g + 1]);
    const double p = sum(pref.back());
    Vector w(instance.n());
    for (int g = 0; g < m; ++g) {
        const auto cdf = reverse_cdf(convolve(pref[g], suff[g + 1]));
        for (int j : instance.groups[g]) w[j] = dot(guide_hist[j], cdf) - p;
    }
    return {p, std::move(w)};
}

double Search::guide_probability(const Selection& s) {
    if (auto it = guide_cache.find(s); it != guide_cache.end()) return it->second;
    if (guide_fft.empty()) {
        if (guide_hist.empty()) gradients(s);
        guide_weight = weights(guide_bins);
        for (const auto& h : guide_hist) guide_fft.push_back(weighted_transform(h, guide_weight));
    }
    Freq<double> freq(guide_bins + 1, 1);
    for (int j : s) multiply(freq, guide_fft[j]);
    return guide_cache[s] = std::clamp(unweighted_sum(freq, guide_weight), 0., 1.);
}

void Search::local_search(double seconds) {
    if (!best) return;
    const double end = std::min(deadline - 10, now() + seconds);
    std::set<Selection> queue{best->selection}, visited;
    for (const auto& s : frontier_candidates)
        if (instance.cost_of(s) < best->cost && guide_probability(s) >= .975) queue.insert(s);
    const auto priority = [&](const Selection& s) {
        return instance.cost_of(s) + std::max(0., .99 + .00015 - guide_probability(s)) * best->cost * 25;
    };
    const auto better = [&](const Selection& a, const Selection& b) {
        return std::make_pair(priority(a), a) < std::make_pair(priority(b), b);
    };
    int rounds = 0;
    while (now() < end && !queue.empty() && rounds < 100) {
        const auto it = std::min_element(queue.begin(), queue.end(), better);
        const auto center = *it;
        queue.erase(it);
        if (!visited.insert(center).second) continue;
        ++rounds;
        auto [p, w] = gradients(center);
        w = negated(std::move(w));
        std::set<Selection> proposals;
        for (int trust : {2, 4, 8, 16}) {
            if (now() > end) break;
            for (double target : {.975, .98, .985, .988, .9901, .992, .995, .999}) {
                if (now() > end) break;
                target = std::min(.99995, target + .99 - .99);
                const auto rows = mip(w, p - target, {}, trust, center, .5, 4);
                proposals.insert(rows.begin(), rows.end());
            }
        }
        const double old = best->cost;
        for (const auto& q : cost_order(proposals)) {
            if (now() > end) break;
            if (instance.cost_of(q) >= best->cost - 1e-8) continue;
            const double prob = guide_probability(q);
            if (prob >= .99 - .00035 && !decisions.count(q)) native_check(q, "CDF_sequential_local_model");
            if (!visited.count(q) && prob >= .982) queue.insert(q);
        }
        if (best->cost < old) queue.insert(best->selection);
        if (queue.size() > 100) {
            Groups ordered(queue.begin(), queue.end());
            std::sort(ordered.begin(), ordered.end(), better);
            queue = {ordered.begin(), ordered.begin() + 100};
        }
    }
    locals.push_back({{"rounds", rounds}, {"visited", visited.size()},
                      {"pending", queue.size()}, {"unique_guides", guide_cache.size()}});
}
std::vector<Search::HalfState> Search::prune(std::vector<HalfState> states) const {
    const int width = std::max(1024, std::min(4096, (40960 / instance.m()) / 512 * 512));
    if (states.size() <= static_cast<std::size_t>(width)) return states;
    const auto bounds = std::minmax_element(states.begin(), states.end(), [](const auto& a, const auto& b) {
        return a.cost < b.cost;
    });
    const double low = bounds.first->cost, range = std::max(1e-9, bounds.second->cost - low);
    Selection buckets, order(states.size());
    for (const auto& s : states) buckets.push_back(std::min(511, int((s.cost - low) / range * 512)));
    std::iota(order.begin(), order.end(), 0);
    std::array<int, 512> counts{};
    std::vector<bool> seen(states.size());
    std::vector<HalfState> result;
    const auto take = [&](int field, int maximum) {
        std::sort(order.begin(), order.end(), [&](int a, int b) {
            const auto key = [&](int k) {
                const auto& s = states[k];
                return std::make_tuple(buckets[k], field == 1 ? -s.p0 : field == 2 ? -s.p1 : 0.f, s.cost, k);
            };
            return key(a) < key(b);
        });
        for (int k : order) {
            if (seen[k] || counts[buckets[k]] >= maximum) continue;
            seen[k] = true;
            ++counts[buckets[k]];
            result.push_back(std::move(states[k]));
        }
    };
    const int slots = width / 512;
    take(0, 1);
    take(1, std::max(2, (slots + 1) / 2));
    take(2, slots);
    if (result.size() > static_cast<std::size_t>(width)) result.resize(width);
    return result;
}

std::vector<Search::HalfState> Search::build_half(const Selection& groups, const Selection& other,
        const std::vector<std::vector<float>>& hist) {
    constexpr int bins = 512;
    const double cap = best->cost;
    const auto minimum_cost = [&](int g) {
        double c = inf;
        for (int j : instance.groups[g]) c = std::min(c, instance.costs[j]);
        return c;
    };
    double rest_min = 0;
    for (int g : other) rest_min += minimum_cost(g);
    std::vector<Vector> suffix(groups.size() + 1);
    suffix.back() = impulse<double>(bins);
    Vector min_suffix(groups.size() + 1);
    for (std::size_t k = groups.size(); k-- > 0;) {
        const int g = groups[k];
        std::vector<float> cdf(bins);
        for (int j : instance.groups[g]) {
            float cumulative = 0;
            for (int b = 0; b < bins; ++b) {
                cumulative += hist[j][b];
                cdf[b] = std::max(cdf[b], cumulative);
            }
        }
        for (int b = bins - 1; b > 0; --b) cdf[b] -= cdf[b - 1];
        suffix[k] = convolve(Vector(cdf.begin(), cdf.end()), suffix[k + 1]);
        min_suffix[k] = min_suffix[k + 1] + minimum_cost(g);
    }
    // Frozen S10 never sets the optional second anchor.
    auto completed = impulse<double>(bins);
    for (int g : other) {
        const auto& row = hist[best->selection[g]];
        completed = convolve(completed, Vector(row.begin(), row.end()));
    }
    std::vector<HalfState> states{{0., 1.f, 1.f, impulse<float>(bins), Selection(instance.m(), -1)}};
    for (std::size_t depth = 0; depth < groups.size(); ++depth) {
        if (remaining() < 5) return {};
        const int g = groups[depth];
        const auto tail = reverse_cdf(convolve(suffix[depth + 1], completed));
        const std::vector<float> cdf(tail.begin(), tail.end());
        const auto& items = instance.groups[g];
        std::vector<Freq<float>> spectra;
        for (int j : items) spectra.push_back(forward(hist[j]));
        std::vector<HalfState> next;
        for (std::size_t i = 0; i < states.size(); ++i) {
            if (i % 64 == 0 && remaining() < 5) return {};
            const auto& state = states[i];
            const auto parent = forward(state.pdf);
            for (std::size_t k = 0; k < items.size(); ++k) {
                const int j = items[k];
                const double cost = state.cost + instance.costs[j];
                if (cost >= cap - rest_min - min_suffix[depth + 1] - 1e-8) continue;
                auto freq = parent;
                multiply(freq, spectra[k]);
                auto pdf = inverse(freq, true);
                const float p = std::clamp(dot(pdf, cdf), 0.f, 1.f);
                auto selection = state.selection;
                selection[g] = j;
                next.push_back({cost, p, p, std::move(pdf), std::move(selection)});
            }
        }
        if (next.empty()) return {};
        states = prune(std::move(next));
    }
    return states;
}

void Search::matching(double delta, const Selection& left, const Selection& right) {
    constexpr int bins = 512;
    std::vector<std::vector<float>> hist;
    for (const auto& row : histograms(bins, delta)) hist.emplace_back(row.begin(), row.end());
    const auto a = build_half(left, right, hist);
    if (a.empty()) return;
    const auto b = build_half(right, left, hist);
    if (b.empty()) return;
    Vector reversed_cdf(bins * b.size());
    for (std::size_t j = 0; j < b.size(); ++j) {
        double p = 0;
        for (int k = 0; k < bins; ++k) {
            p += b[j].pdf[k];
            reversed_cdf[(bins - k - 1) * b.size() + j] = p;
        }
    }
    struct Proposal { std::size_t a, b; double probability, cost; };
    std::vector<Proposal> proposals;
    std::set<std::pair<std::size_t, std::size_t>> seen;
    const double cap = best->cost;
    for (std::size_t first = 0; first < a.size(); first += 64) {
        if (remaining() < 5) break;
        const std::size_t last = std::min(first + 64, a.size()), width = b.size();
        Vector probabilities((last - first) * width), costs(probabilities.size());
        for (std::size_t i = first; i < last; ++i) {
            double* row = probabilities.data() + (i - first) * width;
            for (int k = 0; k < bins; ++k) {
                const double mass = a[i].pdf[k];
                const double* cdf = reversed_cdf.data() + k * width;
                for (std::size_t j = 0; j < width; ++j) row[j] += mass * cdf[j];
            }
            for (std::size_t j = 0; j < width; ++j) {
                row[j] = std::clamp(row[j], 0., 1.);
                costs[(i - first) * width + j] = a[i].cost + b[j].cost;
            }
        }
        for (double fraction : {0., .001, .0025, .005, .01, .02, .03, .05}) {
            Vector scores(costs.size(), -inf);
            int count = 0;
            for (std::size_t k = 0; k < costs.size(); ++k) {
                if (costs[k] >= cap * (1 - fraction) - 1e-8) continue;
                scores[k] = probabilities[k];
                ++count;
            }
            if (count == 0) continue;
            Selection order(scores.size());
            std::iota(order.begin(), order.end(), 0);
            const int split = static_cast<int>(order.size()) - std::min(48, count);
            partition_indices(scores, order.data(), static_cast<int>(order.size()), split);
            for (std::size_t pos = split; pos < order.size(); ++pos) {
                const std::size_t k = order[pos], i = first + k / width, j = k % width;
                if (seen.emplace(i, j).second) proposals.push_back({i, j, probabilities[k], costs[k]});
            }
        }
    }
    std::stable_sort(proposals.begin(), proposals.end(), [](const Proposal& a, const Proposal& b) {
        return std::make_pair(-a.probability, a.cost) < std::make_pair(-b.probability, b.cost);
    });
    const std::string source = "robust_mitm_delta" + Json(delta).dump() + "_left" + join(left);
    int checked = 0;
    for (const auto& q : proposals) {
        if (remaining() < 3 || checked >= 1800) break;
        if (q.probability < .975) continue;
        auto s = a[q.a].selection;
        for (int g : right) s[g] = b[q.b].selection[g];
        native_check(s, source);
        ++checked;
    }
    matches.push_back({{"delta", delta}, {"left", left}, {"right", right}, {"left_states", a.size()},
        {"right_states", b.size()}, {"pair_count", a.size() * b.size()}, {"shortlist", proposals.size()},
        {"checked", checked}, {"remaining", remaining()}});
    save("running");
}

Json Search::shortlist() const {
    std::vector<const Candidate*> ordered;
    for (const auto& entry : pool) ordered.push_back(&entry.second);
    std::sort(ordered.begin(), ordered.end(), [](const auto* a, const auto* b) {
        return std::tie(a->cost, a->selection) < std::tie(b->cost, b->selection);
    });
    Json result = Json::array();
    if (ordered.empty()) return result;
    if (!exhaustive.is_null()) {
        for (const auto* c : ordered) result.push_back(c->json());
        return result;
    }
    const auto score = [&](const Candidate* c) {
        const auto it = guide_cache.find(c->selection);
        return it != guide_cache.end() ? it->second : c->certificate.probability();
    };
    std::set<const Candidate*> keep;
    for (std::size_t i = 0; i < std::min<std::size_t>(32, ordered.size()); ++i) keep.insert(ordered[i]);
    const auto cover = [&](double start, double stop, double step) {
        const int n = static_cast<int>(std::ceil((stop - start) / step));
        const double increment = (start + step) - start;
        for (int i = 0; i < n; ++i) {
            const double level = start + i * increment;
            const auto it = std::find_if(ordered.begin(), ordered.end(), [&](const auto* c) { return score(c) >= level; });
            if (it != ordered.end()) keep.insert(*it);
        }
    };
    cover(.80, .975, .005);
    cover(.975, 1., .00025);
    const auto spacing = std::min<std::size_t>(24, ordered.size());
    if (spacing == 1) keep.insert(ordered[0]);
    else {
        for (std::size_t i = 0; i + 1 < spacing; ++i)
            keep.insert(ordered[std::size_t(i * (double(ordered.size() - 1) / (spacing - 1)))]);
        keep.insert(ordered.back());
    }
    auto high = ordered;
    std::stable_sort(high.begin(), high.end(), [&](const auto* a, const auto* b) {
        return std::make_pair(-score(a), a->cost) < std::make_pair(-score(b), b->cost);
    });
    for (std::size_t i = 0; i < std::min<std::size_t>(8, high.size()); ++i) keep.insert(high[i]);
    for (const auto* c : ordered) {
        if (!keep.count(c)) continue;
        auto record = c->json();
        record["ordering_score"] = score(c);
        result.push_back(std::move(record));
    }
    return result;
}

void Search::final_check() {
    const auto& [s, cost, c, source, found] = *best;
    std::pair<mpz_class, mpz_class> pair;
    if (c.bins) pair = oracle.count(s, c.bins, true);
    else {
        const auto v = SmallCounts(instance, options.capacity).count(s);
        pair = {v.lower, v.denominator};
    }
    if (pair.first != c.lower || pair.second != c.denominator) throw std::logic_error("Integer recount mismatch");
    recomputed = true;
}

Json Search::save(const std::string& status) {
    last_save = now();
    picosha2::hash256_one_by_one digest;
    for (const auto& [s, r] : pool) {
        const auto encoded = Json::array({s, r.cost, r.certificate.lower.get_str(), r.certificate.denominator.get_str()}).dump();
        digest.process(encoded.begin(), encoded.end());
    }
    digest.finish();
    Json selected;
    if (best) {
        selected = best->json();
        selected["probability"] = best->certificate.probability();
        selected["probability_evaluator"] = selected["certificate"]["method"];
        if (recomputed) selected["final_exact_recomputed"] = true;
    }
    Json data = {{"schema", "CCMCKP_S10_raw_constraint_portfolio"}, {"status", status}, {"seed", options.seed},
        {"instance", instance.name}, {"capacity", options.capacity}, {"selected", selected},
        {"candidate_shortlist", status == "completed" ? shortlist() : Json::array()},
        {"raw_certified_pool_count", pool.size()}, {"raw_pool_sha256", hash_text(digest)},
        {"events", events}, {"models", models}, {"model_seconds", model_seconds}, {"match_history", matches},
        {"local_history", locals}, {"exhaustive", exhaustive}, {"ordering_metadata", Json::array()},
        {"auxiliary_grid", nullptr}, {"certificate_calls", oracle.calls}, {"certificate_seconds", oracle.seconds},
        {"runtime_before_save", now() - started},
        {"config", {{"nominal_CL", .99}, {"raw_threshold", ".99"}, {"all_original_samples", true},
            {"tail_hard_gate", false}, {"tail_changes_to_input", false}, {"tail_use", "removed_entirely"},
            {"external_MC_seed", 832273}, {"external_MC_draws", 10000000},
            {"no_dist_metadata_in_optimizer", true}, {"no_cross_run_solutions", true},
            {"search_budget", options.seconds}, {"validation_outside_search_clock", true}}}};
    write_json(options.output, data);
    return data;
}

Json Search::run() {
    std::size_t combinations = 1;
    if (instance.m() <= 5)
        for (const auto& group : instance.groups) {
            if (combinations > 100000 / group.size()) { combinations = 100001; break; }
            combinations *= group.size();
        }
    const auto record = [&](const char* phase, Json metadata, const auto& action) {
        const auto prior = best ? Json(best->cost) : Json(nullptr);
        const auto count = pool.size();
        const double begin = now();
        action();
        metadata["phase"] = phase;
        metadata["elapsed"] = now() - begin;
        metadata["best_before"] = prior;
        metadata["best_after"] = best ? Json(best->cost) : Json(nullptr);
        metadata["candidates_added"] = pool.size() - count;
        phase_records.push_back(std::move(metadata));
    };
    const auto local = [&](const char* phase, double seconds) {
        const bool enabled = options.local_phases == "both" || options.local_phases == phase;
        const std::string name = std::string("local_") + phase;
        record(name.c_str(), {{"enabled", enabled}}, [&] { if (enabled) local_search(seconds); });
    };
    if (instance.m() <= 5 && combinations <= 100000) small_exact_search();
    else {
        record("initialization", Json::object(), [&] { init_frontier(); });
        local("pre", std::min(140., options.seconds * .3));
        if (best) {
            const int m = instance.m();
            Groups left(3), right(3);
            Selection ordered(m);
            Vector range(m);
            std::iota(ordered.begin(), ordered.end(), 0);
            for (int g = 0; g < m; ++g) {
                auto bounds = std::minmax_element(instance.groups[g].begin(), instance.groups[g].end(),
                    [&](int a, int b) { return instance.costs[a] < instance.costs[b]; });
                range[g] = instance.costs[*bounds.first] - instance.costs[*bounds.second];
            }
            // The frozen costs have distinct group ranges.
            std::stable_sort(ordered.begin(), ordered.end(), [&](int a, int b) { return range[a] < range[b]; });
            for (int g = 0; g < m; ++g) {
                (g % 2 ? right[0] : left[0]).push_back(g);
                (g < m / 2 ? left[1] : right[1]).push_back(g);
                (g % 2 ? right[2] : left[2]).push_back(ordered[g]);
            }
            for (double delta : {.00025, 0., .0005, 0.}) {
                for (int part = 0; part < 3 && remaining() >= 15; ++part)
                    record("MITM", {{"delta", delta}, {"left", left[part]}, {"right", right[part]}},
                        [&] { matching(delta, left[part], right[part]); });
                if (remaining() < 15) break;
            }
            if (remaining() > 20) local("post", std::min(30., remaining() - 10));
        }
    }
    if (best) final_check();
    return save("completed");
}
} // namespace s10

