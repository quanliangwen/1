#include "evaluation.hpp"
#include <cmath>
#include <functional>
#include <limits>
#include <numeric>
#include <queue>
#include <set>

namespace s10 {
namespace {
const double infinity = std::numeric_limits<double>::infinity();

mpq_class decimal(std::string value) {
    const auto exponent_position = value.find_first_of("eE");
    int exponent = 0;
    if (exponent_position != std::string::npos) {
        exponent = std::stoi(value.substr(exponent_position + 1));
        value.erase(exponent_position);
    }
    const auto point = value.find('.');
    if (point != std::string::npos) {
        exponent -= static_cast<int>(value.size() - point - 1);
        value.erase(point, 1);
    }
    if (value.front() == '+') value.erase(0, 1);
    const mpz_class numerator(value, 10);
    mpz_class scale;
    mpz_ui_pow_ui(scale.get_mpz_t(), 10, std::abs(exponent));
    mpq_class result = exponent >= 0 ? mpq_class(numerator * scale) : mpq_class(numerator, scale);
    result.canonicalize();
    return result;
}

double ratio(const mpz_class& numerator, const mpz_class& denominator) {
    // GMP truncates its double conversion. Round the rational to nearest-even.
    if (numerator == 0) return 0;
    mpq_class rational(numerator, denominator);
    rational.canonicalize();
    const double lo = rational.get_d(), hi = std::nextafter(lo, infinity);
    const mpq_class midpoint = (mpq_class(lo) + mpq_class(hi)) / 2;
    if (rational < midpoint) return lo;
    if (rational > midpoint) return hi;
    return std::fmod(lo / (hi - lo), 2.) == 0. ? lo : hi;
}
} // namespace

double Certificate::probability() const { return ratio(lower, denominator); }

Json Certificate::json(const Selection& selection) const {
    Json result = {{"selection", selection}, {"lower_numerator", lower.get_str()},
        {"upper_numerator", upper.get_str()}, {"denominator", denominator.get_str()},
        {"lower", probability()}, {"upper", ratio(upper, denominator)}, {"accepted", accepted()},
        {"infeasible", infeasible()}, {"search_threshold", "99/100"}, {"all_original_samples", true},
        {"strict_event", "sum<T"}, {"method", bins ? "exact_integer_upward_grid_count" : "outward_interval_integer_pair_count"}};
    if (bins) {
        result["bins"] = bins;
        result["certificate_seconds"] = seconds;
    }
    return result;
}

SmallCounts::SmallCounts(const Instance& instance, double capacity)
    : instance(instance), tlo(std::nextafter(capacity, -infinity)), thi(std::nextafter(capacity, infinity)) {}

const std::pair<Vector, Vector>& SmallCounts::half(const Selection& selection) {
    auto [entry, fresh] = cache.try_emplace(selection);
    auto& [lo, hi] = entry->second;
    if (fresh) {
        lo = hi = Vector{0};
        for (int j : selection) {
            Vector next_lo, next_hi;
            const auto& a = instance.samples[j];
            next_lo.reserve(lo.size() * a.size());
            next_hi.reserve(hi.size() * a.size());
            Vector a_lo, a_hi;
            for (double x : a) {
                a_lo.push_back(std::nextafter(x, -infinity));
                a_hi.push_back(std::nextafter(x, infinity));
            }
            for (std::size_t k = 0; k < lo.size(); ++k) {
                for (std::size_t i = 0; i < a.size(); ++i) {
                    next_lo.push_back(std::nextafter(lo[k] + a_lo[i], -infinity));
                    next_hi.push_back(std::nextafter(hi[k] + a_hi[i], infinity));
                }
            }
            lo = std::move(next_lo);
            hi = std::move(next_hi);
        }
        std::sort(lo.begin(), lo.end());
        std::sort(hi.begin(), hi.end());
    }
    return entry->second;
}

Certificate SmallCounts::count(const Selection& s) {
    const auto split = s.begin() + s.size() / 2;
    const auto& [al, au] = half(Selection(s.begin(), split));
    const auto& [bl, bu] = half(Selection(split, s.end()));
    unsigned long long lower = 0, upper = 0;
    for (std::size_t i = 0; i < al.size(); ++i) {
        lower += std::lower_bound(bu.begin(), bu.end(), std::nextafter(tlo - au[i], -infinity)) - bu.begin();
        upper += std::lower_bound(bl.begin(), bl.end(), std::nextafter(thi - al[i], infinity)) - bl.begin();
    }
    return {mpz_class(std::to_string(lower)), mpz_class(std::to_string(upper)),
            mpz_class(std::to_string(al.size())) * mpz_class(std::to_string(bl.size()))};
}

ExactOracle::ExactOracle(const Instance& instance, const std::string& capacity)
    : instance(instance), capacity(decimal(capacity)) {}

const Selection& ExactOracle::quantized(int j, int bins, bool up) {
    const auto key = std::make_tuple(j, bins, up);
    if (auto entry = cache.find(key); entry != cache.end()) return entry->second;
    auto [raw, fresh] = ratios.try_emplace(j);
    if (fresh)
        for (const auto& value : instance.decimals[j]) raw->second.push_back(decimal(value) / capacity);
    Selection result;
    for (const auto& x : raw->second) {
        mpz_class n = x.get_num() * bins, d = x.get_den(), q;
        if (up) mpz_cdiv_q(q.get_mpz_t(), n.get_mpz_t(), d.get_mpz_t());
        else mpz_fdiv_q(q.get_mpz_t(), n.get_mpz_t(), d.get_mpz_t());
        result.push_back(q >= bins ? bins : static_cast<int>(q.get_si()));
    }
    return cache.emplace(key, std::move(result)).first->second;
}

std::pair<mpz_class, mpz_class> ExactOracle::count(const Selection& s, int bins, bool up) {
    mpz_class denominator = 1;
    int offset = 0, maximum = 0;
    Selection minima;
    for (int j : s) {
        const auto& indices = quantized(j, bins, up);
        const auto [lo, hi] = std::minmax_element(indices.begin(), indices.end());
        minima.push_back(*lo);
        offset += *lo;
        maximum += *hi;
        denominator *= static_cast<unsigned long>(indices.size());
    }
    const int cut = bins - offset;
    if (cut <= 0) return {0, denominator};
    if (maximum < bins) return {denominator, denominator};

    // Kronecker substitution. A coefficient never exceeds the product of all
    // marginal counts. The fixed-width slots therefore never carry into each other.
    using Word = std::uint32_t;
    constexpr auto word_bits = sizeof(Word) * 8;
    const std::size_t stride = (mpz_sizeinbase(denominator.get_mpz_t(), 2) + word_bits - 1) / word_bits;
    const mp_bitcnt_t cutoff = mp_bitcnt_t(cut) * stride * word_bits;
    std::vector<mpz_class> polynomials;
    for (std::size_t k = 0; k < s.size(); ++k) {
        const auto& indices = quantized(s[k], bins, up);
        const int limit = std::min(cut - 1, *std::max_element(indices.begin(), indices.end()) - minima[k]);
        std::vector<Word> packed(std::size_t(limit + 1) * stride);
        for (int i : indices)
            if (i - minima[k] < cut) ++packed[std::size_t(i - minima[k]) * stride];
        polynomials.emplace_back();
        mpz_import(polynomials.back().get_mpz_t(), packed.size(), -1, sizeof(Word), 0, 0, packed.data());
    }
    while (polynomials.size() > 1) {
        std::vector<mpz_class> next;
        for (std::size_t k = 0; k < polynomials.size(); k += 2) {
            if (k + 1 < polynomials.size()) {
                mpz_class product = polynomials[k] * polynomials[k + 1];
                mpz_fdiv_r_2exp(product.get_mpz_t(), product.get_mpz_t(), cutoff);
                next.push_back(std::move(product));
            } else next.push_back(std::move(polynomials[k]));
        }
        polynomials = std::move(next);
    }
    const auto& polynomial = polynomials.front();
    std::vector<Word> packed((mpz_sizeinbase(polynomial.get_mpz_t(), 2) + word_bits - 1) / word_bits);
    std::size_t used = 0;
    mpz_export(packed.data(), &used, -1, sizeof(Word), 0, 0, polynomial.get_mpz_t());
    mpz_class numerator = 0, coefficient;
    for (std::size_t k = 0; k < used; k += stride) {
        mpz_import(coefficient.get_mpz_t(), std::min(used - k, stride), -1, sizeof(Word), 0, 0, packed.data() + k);
        numerator += coefficient;
    }
    if (numerator > denominator) throw std::logic_error("Invalid exact count");
    return {numerator, denominator};
}

Certificate ExactOracle::certify(const Selection& s, int bins) {
    const double started = now();
    auto [lower, denominator] = count(s, bins, true);
    auto [upper, upper_denominator] = count(s, bins, false);
    if (upper_denominator != denominator || upper < lower) throw std::logic_error("Invalid certificate bounds");
    const double elapsed = now() - started;
    ++calls;
    seconds += elapsed;
    return {std::move(lower), std::move(upper), std::move(denominator), bins, elapsed};
}

Groups native_checks(int L, int m) {
    if (L != 30 && L != 500) return {};
    mpz_class target;
    mpz_ui_pow_ui(target.get_mpz_t(), L, m);
    target /= 100;
    if (target == 0) return {};
    ccmckp::Pcg64 rng(832273);
    Groups result;
    for (int repeat = 0; repeat < 10; ++repeat) {
        Selection factors;
        const auto fill = [&](int count, int value) {
            if (count > 0) factors.insert(factors.end(), count, value);
        };
        if (L == 500) { fill(3*m-2, 5); fill(2*m-2, 2); }
        else { fill(m, 3); fill(m-2, 5); fill(m-2, 2); }
        if (repeat) rng.shuffle(factors);
        Selection products(m, 1);
        bool valid = true;
        for (int f : factors) {
            Selection choices;
            int floor = L + 1;
            for (int i = 0; i < m; ++i) {
                if (products[i] * f > L || products[i] > floor) continue;
                if (products[i] < floor) choices.clear();
                floor = products[i];
                choices.push_back(i);
            }
            if (choices.empty()) { valid = false; break; }
            products[choices[rng.below(static_cast<std::uint32_t>(choices.size()))]] *= f;
        }
        if (!valid) continue;
        mpz_class product = 1;
        for (int x : products) product *= x;
        if (product != target) throw std::logic_error("Invalid native quick-check factorization");
        for (int& x : products) --x;
        for (int j = 0; j < 50; ++j) {
            auto row = products;
            rng.shuffle(row);
            result.push_back(std::move(row));
        }
    }
    return result;
}

Groups lss_checks(int L, int m, ccmckp::LegacyRandom& numpy, ccmckp::PythonRandom& python) {
    Selection factors;
    const auto append_factors = [&](double value) {
        mpz_class n(value);
        for (int f = 2; f <= L && n > 1; ++f) {
            while (mpz_divisible_ui_p(n.get_mpz_t(), f)) {
                n /= f;
                factors.push_back(f);
            }
        }
        if (n > 1) return false;
        if (value == 1 || value == 0) factors.push_back(static_cast<int>(value));
        return true;
    };
    const double ten = std::pow(10., m);
    if (!append_factors(std::pow(double(L / (L >= 100 ? 100 : 10)), m)) ||
        !append_factors(ten / 100.) || (L >= 100 && !append_factors(ten))) return {};
    Groups schedules;
    for (int k = 0; k < 10; ++k) {
        Selection schedule;
        for (;;) {
            numpy.shuffle(factors);
            schedule.assign(m, 1);
            for (std::size_t i = 0; i < factors.size(); ++i) {
                auto& x = schedule[i % m];
                x = std::min(L + 1, x * factors[i]);
            }
            if (*std::max_element(schedule.begin(), schedule.end()) <= L) break;
        }
        for (int& x : schedule) --x;
        std::sort(schedule.begin(), schedule.end());
        if (std::find(schedules.begin(), schedules.end(), schedule) == schedules.end())
            schedules.push_back(std::move(schedule));
    }
    Groups result;
    std::set<Selection> seen;
    for (const auto& schedule : schedules) {
        for (int k = 0; k < 50; ++k) {
            auto pool = schedule;
            Selection row;
            while (!pool.empty()) {
                const int x = pool[python.below(static_cast<std::uint32_t>(pool.size()))];
                row.push_back(x);
                pool.erase(std::find(pool.begin(), pool.end(), x));
            }
            if (seen.insert(row).second) result.push_back(std::move(row));
        }
    }
    return result;
}

LssEvaluator::LssEvaluator(const Instance& instance, double capacity, std::uint32_t seed, std::size_t draws)
    : instance(instance), capacity(capacity), draws(draws),
      exact(std::pow(double(instance.sample_count), instance.m()) < 1e7), numpy(seed) {
    ccmckp::PythonRandom python(seed);
    checks = lss_checks(instance.sample_count, instance.m(), numpy, python);
    numpy.below(832273); // param_test's historical pre-search draw
}

double LssEvaluator::evaluate(const Selection& s) {
    instance.validate(s);
    const int L = instance.sample_count, m = instance.m();
    const double combinations = std::pow(double(L), m);
    const double budget = exact ? combinations * .01 : std::nearbyint(combinations * (1.0 - .99));
    int level = static_cast<int>(std::ceil(std::pow(budget, 1.0 / m)));
    Vector values(m);
    const auto at = [&](const Selection& indices) {
        for (int i = 0; i < m; ++i) values[i] = instance.descending[s[i]].at(indices[i]);
        return sum(values);
    };
    double last = at(Selection(m, level));
    if (last >= capacity) return 0;
    for (const auto& row : checks) {
        last = at(row);
        if (last >= capacity) return 0;
    }
    if (!exact) {
        Vector sums(draws);
        for (int j : s)
            for (double& x : sums) x += instance.samples[j][numpy.below(L - 1)];
        return double(std::count_if(sums.begin(), sums.end(), [&](double x) { return x < capacity; })) / draws;
    }

    while (last < capacity && level > 0) last = at(Selection(m, --level));
    using Entry = std::pair<double, Selection>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> queue;
    std::set<Selection> queued;
    const auto push = [&](const Selection& indices) {
        if (queued.insert(indices).second) queue.emplace(-at(indices), indices);
    };
    Selection row(m);
    const int shell = level + 1;
    const auto enumerate = [&](const auto& self, int depth, bool on_shell) -> void {
        if (depth == m) { if (on_shell) push(row); return; }
        for (int x = 0; x <= shell && x < L; ++x) {
            row[depth] = x;
            self(self, depth + 1, on_shell || x == shell);
        }
    };
    enumerate(enumerate, 0, false);
    double popped_sum = capacity + 1;
    int popped = 0;
    const int maximum = static_cast<int>(std::ceil(budget));
    while (!queue.empty() && popped_sum > capacity) {
        auto [neg, indices] = queue.top();
        queue.pop();
        queued.erase(indices);
        popped_sum = -neg;
        ++popped;
        for (int i = 0; i < m; ++i) {
            if (indices[i] + 1 == L) continue;
            ++indices[i];
            push(indices);
            --indices[i];
        }
        if (popped > maximum) return 0;
    }
    return 1 - (popped + std::pow(double(level + 1), m)) / combinations;
}
} // namespace s10
