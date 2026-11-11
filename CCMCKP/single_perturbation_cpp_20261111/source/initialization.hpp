#pragma once

#include "evaluation.hpp"

namespace ccmckp {

struct Initial {
    Selection selection;
    double cost, probability;
    std::string source;
    std::uint64_t repairs = 0;
};

Initial initialize(const Instance& instance, const Settings& settings,
                   const std::function<double(const Selection&)>& evaluate,
                   const Stop& stopped);

} // namespace ccmckp
