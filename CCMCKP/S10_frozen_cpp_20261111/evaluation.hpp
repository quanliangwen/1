#pragma once
#include "model.hpp"
#include "rng.hpp"
#include <gmpxx.h>
#include <map>

namespace s10 {
struct Certificate {
    mpz_class lower, upper, denominator;
    int bins = 0;
    double seconds = 0;
    bool accepted() const { return lower * 100 >= denominator * 99; }
    bool infeasible() const { return upper * 100 < denominator * 99; }
    double probability() const;
    Json json(const Selection& selection) const;
};

class SmallCounts {
public:
    SmallCounts(const Instance& instance, double capacity);
    Certificate count(const Selection& selection);
private:
    const std::pair<Vector, Vector>& half(const Selection& selection);
    const Instance& instance;
    double tlo, thi;
    std::map<Selection, std::pair<Vector, Vector>> cache;
};

class ExactOracle {
public:
    ExactOracle(const Instance& instance, const std::string& capacity);
    const Selection& quantized(int item, int bins, bool up);
    std::pair<mpz_class, mpz_class> count(const Selection& selection, int bins, bool up);
    Certificate certify(const Selection& selection, int bins);
    int calls = 0;
    double seconds = 0;
private:
    const Instance& instance;
    mpq_class capacity;
    std::map<int, std::vector<mpq_class>> ratios;
    std::map<std::tuple<int, int, bool>, Selection> cache;
};

Groups native_checks(int samples, int groups);
Groups lss_checks(int samples, int groups, ccmckp::LegacyRandom& numpy, ccmckp::PythonRandom& python);
class LssEvaluator {
public:
    LssEvaluator(const Instance& instance, double capacity, std::uint32_t seed, std::size_t draws = 1000000);
    double evaluate(const Selection& selection);
    const Groups& quick_checks() const { return checks; }
private:
    const Instance& instance;
    double capacity;
    std::size_t draws;
    bool exact;
    ccmckp::LegacyRandom numpy;
    Groups checks;
};
} // namespace s10
