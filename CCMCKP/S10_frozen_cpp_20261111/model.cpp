#include "model.hpp"
#include "third_party/picosha2.h"
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <numeric>
#include <sstream>

namespace s10 {
double sum(const double* data, std::size_t size) {
    if (size < 8) {
        double result = -0.0;
        for (std::size_t i = 0; i < size; ++i) result += data[i];
        return result;
    }
    if (size > 128) {
        const auto half = (size / 2) & ~std::size_t(7);
        return sum(data, half) + sum(data + half, size - half);
    }
    std::array<double, 8> lanes;
    std::copy_n(data, lanes.size(), lanes.begin());
    const auto blocks = size - size % 8;
    for (std::size_t i = 8; i < blocks; i += 8)
        for (std::size_t j = 0; j < 8; ++j) lanes[j] += data[i + j];
    double result = ((lanes[0] + lanes[1]) + (lanes[2] + lanes[3])) +
                    ((lanes[4] + lanes[5]) + (lanes[6] + lanes[7]));
    for (std::size_t i = blocks; i < size; ++i) result += data[i];
    return result;
}

double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

std::string sha256(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Cannot open " + path.string());
    return picosha2::hash256_hex_string(std::istreambuf_iterator<char>(input), {});
}

Json read_json(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Cannot open " + path.string());
    return Json::parse(input);
}

void write_json(const fs::path& path, const Json& data) {
    auto temporary = path;
    temporary += ".tmp";
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    output << data.dump() << '\n';
    output.close();
    if (!output) throw std::runtime_error("Cannot write " + path.string());
    fs::rename(temporary, path);
}

namespace {
Vector read_values(const fs::path& path, std::vector<std::string>* decimals = nullptr) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Cannot open " + path.string());
    Vector result;
    for (std::string line; std::getline(file, line);) {
        std::istringstream row(line.substr(0, line.find('#')));
        for (std::string token; row >> token;) {
            std::size_t end = 0;
            const double x = std::stod(token, &end);
            if (end != token.size() || !std::isfinite(x))
                throw std::runtime_error("Invalid number in " + path.string());
            result.push_back(x);
            if (decimals) decimals->push_back(token);
        }
    }
    if (result.empty()) throw std::runtime_error("Empty file " + path.string());
    return result;
}

// Parse only data opcodes for the benchmark's dict/list of integer lists.
class GroupPickle {
public:
    explicit GroupPickle(const fs::path& path) : in(path, std::ios::binary) {}

    Groups read() {
        expect(0x80);
        const int protocol = byte();
        if (protocol < 2 || protocol > 5) fail();
        const int root = byte_after_frames();
        if (root != '}' && root != ']') fail();
        memo();
        std::map<int, Selection> keyed;
        const bool marked = peek() == '(';
        if (marked) byte();
        while (peek() != '.' && peek() != 'u' && peek() != 'e') {
            const int key = root == '}' ? integer() : static_cast<int>(keyed.size());
            expect(']');
            memo();
            Selection row;
            if (peek() == '(') {
                byte();
                while (peek() != 'e') row.push_back(integer());
                expect('e');
            } else {
                while (peek() == 'K' || peek() == 'M' || peek() == 'J') {
                    row.push_back(integer());
                    expect('a');
                }
            }
            if (!keyed.emplace(key, std::move(row)).second) fail();
            if (!marked) expect(root == '}' ? 's' : 'a');
        }
        if (marked) expect(root == '}' ? 'u' : 'e');
        expect('.');
        if (in.peek() != EOF) fail();
        Groups groups;
        for (auto& entry : keyed) groups.push_back(std::move(entry.second));
        return groups;
    }

private:
    [[noreturn]] static void fail() { throw std::runtime_error("Unsupported or invalid node_to_factor.pkl"); }
    int byte() {
        const int b = in.get();
        if (b == EOF) fail();
        return b;
    }
    int peek() {
        while (in.peek() == 0x95) {
            byte();
            for (int i = 0; i < 8; ++i) byte();
        }
        return in.peek();
    }
    int byte_after_frames() { peek(); return byte(); }
    void expect(int opcode) { if (byte_after_frames() != opcode) fail(); }
    void memo() {
        switch (peek()) {
        case 0x94: byte(); break;
        case 'q': byte(); byte(); break;
        case 'r':
            byte();
            for (int i = 0; i < 4; ++i) byte();
            break;
        }
    }
    int integer() {
        const int opcode = byte_after_frames();
        const int size = opcode == 'K' ? 1 : opcode == 'M' ? 2 : opcode == 'J' ? 4 : 0;
        if (!size) fail();
        std::uint32_t value = 0;
        for (int i = 0; i < size; ++i) value |= std::uint32_t(byte()) << (8 * i);
        if (value > std::uint32_t(std::numeric_limits<int>::max())) fail();
        return static_cast<int>(value);
    }
    std::ifstream in;
};
} // namespace

Instance::Instance(fs::path directory)
    : path(fs::canonical(directory)), name(path.filename().string()),
      groups(GroupPickle(path / "node_to_factor.pkl").read()), costs(read_values(path / "cost.txt")) {
    std::vector<bool> found(n());
    if (groups.empty()) throw std::runtime_error("No groups");
    for (const auto& group : groups) {
        if (group.empty()) throw std::runtime_error("Empty group");
        for (int j : group) {
            if (j < 0 || j >= n() || found[j]) throw std::runtime_error("Groups must partition item IDs");
            found[j] = true;
        }
    }
    if (std::find(found.begin(), found.end(), false) != found.end())
        throw std::runtime_error("Groups must cover all item IDs");
    for (int j = 0; j < n(); ++j) {
        decimals.emplace_back();
        samples.push_back(read_values(path / (std::to_string(j) + "_sample.txt"), &decimals.back()));
        const auto& a = samples.back();
        if (j == 0) sample_count = static_cast<int>(a.size());
        if (a.size() != static_cast<std::size_t>(sample_count) || a.size() < 2 ||
            *std::min_element(a.begin(), a.end()) < 0)
            throw std::runtime_error("Expected equal-length nonnegative samples");
        const double mu = sum(a) / a.size();
        Vector sq;
        for (double x : a) sq.push_back((x - mu) * (x - mu));
        const double ss = sum(sq);
        mean.push_back(mu);
        variance.push_back(ss / a.size());
        sd.push_back(std::sqrt(ss / (a.size() - 1)));
        descending.push_back(a);
        std::sort(descending.back().begin(), descending.back().end(), std::greater<double>());
    }
}

void Instance::validate(const Selection& selection) const {
    if (selection.size() != groups.size()) throw std::runtime_error("Wrong number of selected items");
    for (std::size_t g = 0; g < groups.size(); ++g)
        if (std::find(groups[g].begin(), groups[g].end(), selection[g]) == groups[g].end())
            throw std::runtime_error("Expected one selected item per group in group order");
}

double Instance::cost_of(const Selection& selection) const {
    Vector values;
    for (int j : selection) values.push_back(costs[j]);
    return sum(values);
}

double Instance::lss_cost(const Selection& selection) const {
    double cost = 0;
    for (int j : selection) cost += costs[j];
    return cost;
}
} // namespace s10
