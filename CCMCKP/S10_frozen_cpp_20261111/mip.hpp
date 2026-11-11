#pragma once
#include "model.hpp"
#include <limits>
#include <memory>

namespace s10 {
struct LinearRow {
    Vector coefficients;
    double lower = -std::numeric_limits<double>::infinity();
    double upper = std::numeric_limits<double>::infinity();
};

class BinaryModel {
public:
    BinaryModel(const Instance& instance, std::string backend, int seed);
    ~BinaryModel();
    Groups solve(const Vector& objective, const std::vector<LinearRow>& rows, double seconds, int pool);
private:
    struct Impl;
    std::unique_ptr<Impl> impl;
};
} // namespace s10
