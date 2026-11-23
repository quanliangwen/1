#pragma once
#include "third_party/json.hpp"
#include <filesystem>
#include <string>
#include <vector>

namespace s10 {
namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
using Vector = std::vector<double>;
using Selection = std::vector<int>;
using Groups = std::vector<Selection>;

double sum(const double* data, std::size_t size);
inline double sum(const Vector& data) { return sum(data.data(), data.size()); }
double now();
std::string sha256(const fs::path& path);
Json read_json(const fs::path& path);
void write_json(const fs::path& path, const Json& data);

struct Instance {
    explicit Instance(fs::path directory);
    double cost_of(const Selection& selection) const;
    double lss_cost(const Selection& selection) const;
    void validate(const Selection& selection) const;

    fs::path path;
    std::string name;
    Groups groups;
    Vector costs, mean, variance, sd;
    std::vector<Vector> samples, descending;
    std::vector<std::vector<std::string>> decimals;
    int sample_count;
    int m() const { return static_cast<int>(groups.size()); }
    int n() const { return static_cast<int>(costs.size()); }
};
} // namespace s10
