#include "model.hpp"

#include <cmath>
#include <fstream>
#include <limits>
#include <locale>
#include <numeric>
#include <regex>
#include <sstream>

namespace ccmckp {

double numpy_sum(const double* values, std::size_t count) {
    if (count < 8) {
        double sum = -0.0;
        for (std::size_t i = 0; i < count; ++i) sum += values[i];
        return sum;
    }
    if (count > 128) {
        const auto half = (count / 2) & ~std::size_t(7);
        return numpy_sum(values, half) + numpy_sum(values + half, count - half);
    }
    std::array<double, 8> lanes;
    std::copy_n(values, lanes.size(), lanes.begin());
    const auto blocks = count - count % 8;
    for (std::size_t i = 8; i < blocks; i += 8) {
        for (std::size_t j = 0; j < 8; ++j) lanes[j] += values[i + j];
    }
    double sum = ((lanes[0] + lanes[1]) + (lanes[2] + lanes[3])) +
                 ((lanes[4] + lanes[5]) + (lanes[6] + lanes[7]));
    for (std::size_t i = blocks; i < count; ++i) sum += values[i];
    return sum;
}

namespace {

std::vector<double> read_numbers(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open " + path.string());
    std::vector<double> values;
    std::string line;
    while (std::getline(input, line)) {
        const auto comment = line.find('#');
        std::istringstream tokens(line.substr(0, comment));
        tokens.imbue(std::locale::classic());
        double number;
        while (tokens >> number) {
            if (!std::isfinite(number)) throw std::runtime_error("non-finite input " + path.string());
            values.push_back(number);
        }
        if (!tokens.eof()) throw std::runtime_error("invalid number in " + path.string());
    }
    return values;
}

// The benchmark pickle is a plain dict<int, list<int>>. Interpret only the
// data opcodes needed by that schema, never executable pickle instructions.
class GroupPickle {
public:
    explicit GroupPickle(const std::filesystem::path& path) : input_(path, std::ios::binary) {
        if (!input_) throw std::runtime_error("cannot open " + path.string());
    }

    Groups read(int classes, int per_class) {
        Groups rows(classes);
        expect(0x80);
        const auto protocol = byte();
        if (protocol < 2 || protocol > 5) fail();
        expect('}');
        memo();
        const bool bulk = peek() == '(';
        if (bulk) byte();
        for (int count = 0; count < classes; ++count) {
            const auto key = integer();
            if (key >= static_cast<std::uint32_t>(classes) || !rows[key].empty()) fail();
            expect(']');
            memo();
            auto& row = rows[key];
            const bool appends = peek() == '(';
            if (appends) byte();
            for (int i = 0; i < per_class; ++i) {
                const auto item = integer();
                if (item >= static_cast<std::uint64_t>(classes) * per_class) fail();
                row.push_back(static_cast<int>(item));
                if (!appends) expect('a');
            }
            if (appends) expect('e');
            if (!bulk) expect('s');
        }
        if (bulk) expect('u');
        expect('.');
        if (input_.peek() != EOF) fail();
        return rows;
    }

private:
    [[noreturn]] static void fail() { throw std::runtime_error("unsupported or invalid node_to_factor.pkl"); }

    int byte() {
        const int value = input_.get();
        if (value == EOF) fail();
        return value;
    }

    int peek() {
        while (input_.peek() == 0x95) {
            byte();
            for (int i = 0; i < 8; ++i) byte(); // FRAME length
        }
        return input_.peek();
    }

    void expect(int opcode) {
        if (peek() != opcode) fail();
        byte();
    }

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

    std::uint32_t integer() {
        const int opcode = peek();
        byte();
        int size;
        if (opcode == 'K') size = 1;
        else if (opcode == 'M') size = 2;
        else if (opcode == 'J') size = 4;
        else fail();
        std::uint32_t result = 0;
        for (int i = 0; i < size; ++i) result |= std::uint32_t(byte()) << (i * 8);
        return result;
    }

    std::ifstream input_;
};

// NumPy's indirect quicksort chooses the median of three and insertion-sorts
// short partitions. Preserve its order for equal keys, including 20-item groups.
template <class Less>
void numpy_argsort(Selection& ids, int first, int last, int depth, const Less& less) {
    while (last - first > 15) {
        if (depth < 0) {
            // NumPy's fallback is the same max-heap selection with left-child
            // precedence on equal keys and a strict comparison when sinking.
            const auto sink = [&](int root, int end, int value) {
                int child = root * 2 + 1;
                while (child < end) {
                    if (child + 1 < end && less(ids[first + child], ids[first + child + 1])) ++child;
                    if (!less(value, ids[first + child])) break;
                    ids[first + root] = ids[first + child];
                    root = child;
                    child = root * 2 + 1;
                }
                ids[first + root] = value;
            };
            const int size = last - first + 1;
            for (int root = size / 2 - 1; root >= 0; --root) sink(root, size, ids[first + root]);
            for (int end = size - 1; end > 0; --end) {
                const int value = ids[first + end];
                ids[first + end] = ids[first];
                sink(0, end, value);
            }
            return;
        }
        const int middle = first + (last - first) / 2;
        if (less(ids[middle], ids[first])) std::swap(ids[middle], ids[first]);
        if (less(ids[last], ids[middle])) std::swap(ids[last], ids[middle]);
        if (less(ids[middle], ids[first])) std::swap(ids[middle], ids[first]);
        const int pivot = ids[middle];
        int left = first, right = last - 1;
        std::swap(ids[middle], ids[right]);
        while (true) {
            do { ++left; } while (less(ids[left], pivot));
            do { --right; } while (less(pivot, ids[right]));
            if (left >= right) break;
            std::swap(ids[left], ids[right]);
        }
        std::swap(ids[left], ids[last - 1]);
        --depth;
        if (left - first < last - left) {
            numpy_argsort(ids, first, left - 1, depth, less);
            first = left + 1;
        } else {
            numpy_argsort(ids, left + 1, last, depth, less);
            last = left - 1;
        }
    }
    for (int i = first + 1; i <= last; ++i) {
        const int item = ids[i];
        int j = i;
        while (j > first && less(item, ids[j - 1])) {
            ids[j] = ids[j - 1];
            --j;
        }
        ids[j] = item;
    }
}

template <class Key>
Selection descending_order(Selection ids, const Key& key) {
    int depth = 0;
    for (auto size = ids.size(); size > 1; size >>= 1) depth += 2;
    numpy_argsort(ids, 0, static_cast<int>(ids.size()) - 1, depth,
                  [&](int a, int b) { return key(a) < key(b); });
    std::reverse(ids.begin(), ids.end());
    return ids;
}

bool dominates(const Item& a, const Item& b, int aid, int bid) {
    if (a.cost > b.cost + tolerance) return false;
    bool strict = a.cost < b.cost - tolerance;
    for (std::size_t i = 0; i < a.descending.size(); ++i) {
        if (a.descending[i] > b.descending[i] + tolerance) return false;
        strict |= a.descending[i] < b.descending[i] - tolerance;
    }
    return strict || aid < bid;
}

double variance(const std::vector<double>& samples, int count, double mean, int ddof) {
    std::vector<double> squares(count);
    for (int i = 0; i < count; ++i) {
        const double delta = samples[i] - mean;
        squares[i] = delta * delta;
    }
    return numpy_sum(squares.data(), squares.size()) / (count - ddof);
}

} // namespace

double Instance::cost(const Selection& selection) const {
    double total = 0.0;
    for (int fid : selection) total += items[fid].cost;
    return total;
}

Instance read_instance(const std::filesystem::path& directory, double lambda) {
    Instance instance{};
    instance.name = std::filesystem::absolute(directory).lexically_normal().filename().string();
    if (instance.name.empty() || instance.name == ".") {
        instance.name = std::filesystem::weakly_canonical(directory).filename().string();
    }
    const std::regex digits("[0-9]+");
    auto match = std::sregex_iterator(instance.name.begin(), instance.name.end(), digits);
    for (int* target : {&instance.classes, &instance.items_per_class, &instance.sample_count}) {
        if (match == std::sregex_iterator()) throw std::runtime_error("instance name needs m, N, L");
        *target = std::stoi(match++->str());
    }
    const int m = instance.classes, n = instance.items_per_class, l = instance.sample_count;
    if (m < 1 || n < 1 || l < 2 || m > std::numeric_limits<int>::max() / n) {
        throw std::runtime_error("invalid instance dimensions");
    }
    instance.combinations = integer_power_as_double(l, m);
    if (!std::isfinite(instance.combinations)) throw std::runtime_error("L^m overflows double");
    const auto costs = read_numbers(directory / "cost.txt");
    if (costs.size() < static_cast<std::size_t>(m * n)) throw std::runtime_error("missing costs");
    const double max_cost = *std::max_element(costs.begin(), costs.end());
    const auto groups = GroupPickle(directory / "node_to_factor.pkl").read(m, n);
    instance.items.reserve(m * n);
    std::vector<bool> seen(m * n);
    for (const auto& group : groups) {
        for (const int fid : group) {
            if (seen[fid]) throw std::runtime_error("factor ID occurs in multiple group positions");
            seen[fid] = true;
        }
    }
    for (int fid = 0; fid < m * n; ++fid) {
        Item item{};
        item.cost = costs[fid];
        item.samples = read_numbers(directory / (std::to_string(fid) + "_sample.txt"));
        if (item.samples.size() != static_cast<std::size_t>(l)) throw std::runtime_error("wrong sample count");
        item.descending = item.samples;
        std::sort(item.descending.begin(), item.descending.end(), std::greater<double>{});
        const double mean = numpy_sum(item.samples.data(), l) / l;
        item.weight = mean + lambda * std::sqrt(variance(item.samples, l, mean, 1));
        const double value = max_cost - item.cost;
        item.utility = item.weight == 0.0 ? std::numeric_limits<double>::infinity() : value / item.weight;
        item.mean = numpy_sum(item.samples.data(), l - 1) / (l - 1);
        item.variance = variance(item.samples, l - 1, item.mean, 0);
        instance.items.push_back(std::move(item));
    }
    for (const auto& group : groups) {
        auto weight = descending_order(group, [&](int fid) { return instance.items[fid].weight; });
        auto utility = descending_order(group, [&](int fid) { return instance.items[fid].utility; });
        auto value = descending_order(group, [&](int fid) { return max_cost - instance.items[fid].cost; });
        std::vector<bool> removed(m * n);
        for (int b : value) {
            for (int a : value) {
                if (a != b && dominates(instance.items[a], instance.items[b], a, b)) {
                    removed[b] = true;
                    break;
                }
            }
        }
        if (std::all_of(value.begin(), value.end(), [&](int fid) { return removed[fid]; })) {
            removed[*std::min_element(value.begin(), value.end())] = false;
        }
        for (auto* order : {&weight, &utility, &value}) {
            order->erase(std::remove_if(order->begin(), order->end(),
                         [&](int fid) { return removed[fid]; }), order->end());
        }
        instance.weight.push_back(std::move(weight));
        instance.utility.push_back(std::move(utility));
        instance.value.push_back(std::move(value));
    }
    return instance;
}

} // namespace ccmckp
