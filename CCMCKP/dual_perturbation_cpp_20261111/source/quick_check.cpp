#include "model.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
#include <numeric>
#include <regex>
#include <set>
#include <sstream>
#include <thread>
#if defined(_WIN32)
#include <process.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>
#endif

namespace ccmckp {
namespace {

// The Python quick check factors integers converted from math.pow(double).
// Preserve all bits of those integers, including the rounded low bits at large m.
class Integer {
public:
    explicit Integer(double value) {
        if (!std::isfinite(value) || value < 0.0) throw std::runtime_error("invalid QuickCheck product");
        int exponent;
        const double fraction = std::frexp(value, &exponent);
        if (exponent <= 0) return;
        const auto mantissa = static_cast<std::uint64_t>(std::ldexp(fraction, 53));
        for (int bit = 0; bit < 53; ++bit) {
            const int index = exponent - 53 + bit;
            if (index < 0 || !(mantissa & (std::uint64_t(1) << bit))) continue;
            if (limbs_.size() <= static_cast<std::size_t>(index / 32)) limbs_.resize(index / 32 + 1);
            limbs_[index / 32] |= std::uint32_t(1) << (index % 32);
        }
    }

    void multiply(std::uint32_t by) {
        std::uint64_t carry = 0;
        for (auto& limb : limbs_) {
            const auto product = std::uint64_t(limb) * by + carry;
            limb = product;
            carry = product >> 32;
        }
        if (carry) limbs_.push_back(carry);
    }

    std::uint32_t mod(std::uint32_t by) const {
        std::uint64_t carry = 0;
        for (auto i = limbs_.rbegin(); i != limbs_.rend(); ++i) {
            carry = ((carry << 32) | *i) % by;
        }
        return carry;
    }

    std::uint32_t divide(std::uint32_t by) {
        std::uint64_t carry = 0;
        for (auto i = limbs_.rbegin(); i != limbs_.rend(); ++i) {
            const auto dividend = (carry << 32) | *i;
            *i = dividend / by;
            carry = dividend % by;
        }
        while (!limbs_.empty() && limbs_.back() == 0) limbs_.pop_back();
        return carry;
    }

    double to_double() const {
        if (limbs_.empty()) return 0;
        Integer copy = *this;
        std::vector<std::uint32_t> decimal;
        while (!copy.limbs_.empty()) decimal.push_back(copy.divide(1000000000));
        std::ostringstream output;
        output.imbue(std::locale::classic());
        output << decimal.back() << std::setfill('0');
        for (auto i = decimal.rbegin() + 1; i != decimal.rend(); ++i) output << std::setw(9) << *i;
        return std::strtod(output.str().c_str(), nullptr);
    }

private:
    std::vector<std::uint32_t> limbs_;
};

struct QuickCheckTimeout {};

class CacheLock {
public:
    CacheLock(std::filesystem::path lock_path, Deadline deadline) : path_(std::move(lock_path)) {
#if defined(_WIN32)
        path_ += ".d";
        while (!std::filesystem::create_directory(path_)) wait(deadline);
#else
        fd_ = ::open(path_.c_str(), O_CREAT | O_RDWR, 0644);
        if (fd_ < 0) throw std::runtime_error("cannot open QuickCheck cache lock");
        try {
            while (::flock(fd_, LOCK_EX | LOCK_NB) != 0) {
                if (errno != EWOULDBLOCK && errno != EINTR) {
                    throw std::runtime_error("cannot acquire QuickCheck cache lock");
                }
                wait(deadline);
            }
        } catch (...) {
            ::close(fd_);
            throw;
        }
#endif
    }

    ~CacheLock() {
#if defined(_WIN32)
        std::error_code error;
        std::filesystem::remove(path_, error);
#else
        ::close(fd_);
#endif
    }

    CacheLock(const CacheLock&) = delete;
    CacheLock& operator=(const CacheLock&) = delete;

private:
    static void wait(Deadline deadline) {
        if (Clock::now() >= deadline) throw QuickCheckTimeout{};
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    std::filesystem::path path_;
#if !defined(_WIN32)
    int fd_;
#endif
};

bool append_factors(double value, int sample_count, Selection& factors, Deadline deadline) {
    Integer remaining(value);
    const auto check_time = [&] {
        if (Clock::now() >= deadline) throw QuickCheckTimeout{};
    };
    std::uint32_t divisor = 2;
    for (;;) {
        const double number = remaining.to_double();
        const double root = std::floor(std::pow(number, 0.5));
        while (divisor <= root) {
            if ((divisor & 255u) == 0) check_time();
            if (remaining.mod(divisor) == 0) break;
            ++divisor;
        }
        if (divisor > root) {
            if (number > sample_count) return false;
            factors.push_back(static_cast<int>(number));
            return true;
        }
        if (divisor > static_cast<std::uint32_t>(sample_count)) return false;
        factors.push_back(divisor);
        remaining.divide(divisor);
    }
}

std::uint64_t sha256_first64(const std::string& input) {
    constexpr std::uint32_t constants[] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    std::array<std::uint32_t, 8> state{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    std::vector<std::uint8_t> bytes(input.begin(), input.end());
    bytes.push_back(128);
    while (bytes.size() % 64 != 56) bytes.push_back(0);
    const auto bits = static_cast<std::uint64_t>(input.size()) * 8;
    for (int shift = 56; shift >= 0; shift -= 8) bytes.push_back(bits >> shift);
    const auto rotate = [](std::uint32_t word, int n) { return (word >> n) | (word << (32 - n)); };
    for (std::size_t block = 0; block < bytes.size(); block += 64) {
        std::array<std::uint32_t, 64> words{};
        for (int i = 0; i < 64; ++i) words[i / 4] = (words[i / 4] << 8) | bytes[block + i];
        for (int i = 16; i < 64; ++i) {
            const auto a = words[i - 15], b = words[i - 2];
            const auto s0 = rotate(a, 7) ^ rotate(a, 18) ^ (a >> 3);
            const auto s1 = rotate(b, 17) ^ rotate(b, 19) ^ (b >> 10);
            words[i] = words[i - 16] + s0 + words[i - 7] + s1;
        }
        auto [a,b,c,d,e,f,g,h] = state;
        for (int i = 0; i < 64; ++i) {
            const auto s1 = rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25);
            const auto t1 = h + s1 + ((e & f) ^ (~e & g)) + constants[i] + words[i];
            const auto s0 = rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22);
            const auto t2 = s0 + ((a & b) ^ (a & c) ^ (b & c));
            h = g; g = f; f = e; e = d + t1;
            d = c; c = b; b = a; a = t1 + t2;
        }
        const std::array<std::uint32_t, 8> add{a,b,c,d,e,f,g,h};
        for (std::size_t i = 0; i < state.size(); ++i) state[i] += add[i];
    }
    return (std::uint64_t(state[0]) << 32) | state[1];
}

Groups build_rows(int l, int m, double p0, std::uint32_t seed, Deadline deadline) {
    const int base = l >= 100 ? l / 100 : l / 10;
    const double power = std::pow(10.0, m);
    const double reciprocal = std::nearbyint(1.0 / (1.0 - p0));
    Selection factors;
    if (!append_factors(std::pow(base, m), l, factors, deadline) ||
        !append_factors(power / reciprocal, l, factors, deadline) ||
        (l >= 100 && !append_factors(power, l, factors, deadline))) return {};

    LegacyRandom numpy(seed);
    // CPython's random module re-seeds from OS entropy after the original
    // QuickCheck worker forks. NumPy retains the instance-specific seed.
    std::random_device entropy;
    std::vector<std::uint32_t> seed_words(624);
    for (auto& word : seed_words) word = entropy();
    PythonRandom python(seed_words);
    Groups schedules;
    for (int i = 0; i < 10; ++i) {
        Selection schedule;
        while (true) {
            if (Clock::now() >= deadline) throw QuickCheckTimeout{};
            numpy.shuffle(factors);
            std::vector<std::int64_t> products(m, 1);
            for (std::size_t j = 0; j < factors.size(); ++j) {
                auto& product = products[j % m];
                product = std::min<std::int64_t>(l + 1, product * factors[j]);
            }
            if (*std::max_element(products.begin(), products.end()) <= l) {
                for (const auto product : products) schedule.push_back(static_cast<int>(product - 1));
                break;
            }
        }
        if (*std::min_element(schedule.begin(), schedule.end()) < 0) {
            throw std::runtime_error("QuickCheck product is zero for this confidence/dimension");
        }
        std::sort(schedule.begin(), schedule.end());
        if (std::find(schedules.begin(), schedules.end(), schedule) == schedules.end()) {
            schedules.push_back(std::move(schedule));
        }
    }

    Groups rows;
    std::set<Selection> seen;
    for (const auto& schedule : schedules) {
        if (schedule.size() == 1) throw std::runtime_error("reference QuickCheck requires multiple classes");
        for (int i = 0; i < 50; ++i) {
            if (Clock::now() >= deadline) throw QuickCheckTimeout{};
            Selection remaining = schedule, row;
            while (!remaining.empty()) {
                const int value = remaining[python.below(remaining.size())];
                row.push_back(value);
                // Python list.remove erases the first equal value, even when
                // random.choice picked a later duplicate.
                remaining.erase(std::find(remaining.begin(), remaining.end(), value));
            }
            if (seen.insert(row).second) rows.push_back(std::move(row));
        }
    }
    return rows;
}

bool read_cache(const std::filesystem::path& file, const Instance& instance, double p0, Groups& rows) {
    std::ifstream input(file);
    if (!input) return false;
    const std::string json((std::istreambuf_iterator<char>(input)), {});
    const auto scalar = [&](const char* field) {
        const std::regex pattern(std::string("\"") + field + "\"\\s*:\\s*(\"[^\"]*\"|[-+.eE0-9]+)");
        std::smatch match;
        return std::regex_search(json, match, pattern) ? match[1].str() : std::string{};
    };
    try {
        if (scalar("instance") != "\"" + instance.name + "\"" || scalar("cache_version") != "2" ||
            scalar("m") != std::to_string(instance.classes) ||
            scalar("L") != std::to_string(instance.sample_count) ||
            scalar("list_size") != "10" || scalar("K") != "50" ||
            std::abs(std::stod(scalar("p0")) - p0) > tolerance) return false;
        const auto key = json.find("\"quick_check_list\"");
        if (key == std::string::npos) return false;
        const auto start = json.find('[', key);
        if (start == std::string::npos) return false;
        std::istringstream stream(json.substr(start));
        char token;
        stream >> token;
        if (!(stream >> token)) return false;
        Groups parsed;
        while (token == '[') {
            Selection row;
            for (int i = 0; i < instance.classes; ++i) {
                int value;
                if (!(stream >> value >> token) || value < 0 || value >= instance.sample_count ||
                    token != (i + 1 == instance.classes ? ']' : ',')) return false;
                row.push_back(value);
            }
            parsed.push_back(std::move(row));
            if (!(stream >> token)) return false;
            if (token != ',') break;
            if (!(stream >> token) || token != '[') return false;
        }
        if (token != ']') return false;
        rows = std::move(parsed);
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

void write_cache(const std::filesystem::path& file, const Instance& instance,
                 double p0, std::uint32_t seed, const Groups& rows) {
    auto temporary = file;
#if defined(_WIN32)
    temporary += ".tmp." + std::to_string(_getpid());
#else
    temporary += ".tmp." + std::to_string(::getpid());
#endif
    try {
        std::ofstream out(temporary);
        out.exceptions(std::ios::failbit | std::ios::badbit);
        out.imbue(std::locale::classic());
        out << "{\"cache_version\":2,\"instance\":" << std::quoted(instance.name)
            << ",\"m\":" << instance.classes << ",\"L\":" << instance.sample_count
            << ",\"p0\":" << std::setprecision(17) << p0 << ",\"list_size\":10,\"K\":50"
            << ",\"construction_seed\":" << seed << ",\"quick_check_list\":[";
        for (std::size_t i = 0; i < rows.size(); ++i) {
            if (i) out << ',';
            out << '[';
            for (std::size_t j = 0; j < rows[i].size(); ++j) {
                if (j) out << ',';
                out << rows[i][j];
            }
            out << ']';
        }
        out << "]}\n";
        out.close();
        std::filesystem::rename(temporary, file);
    } catch (...) {
        std::error_code error;
        std::filesystem::remove(temporary, error);
        throw;
    }
}

} // namespace

double integer_power_as_double(int base, int exponent) {
    Integer product(1.0);
    for (int i = 0; i < exponent; ++i) product.multiply(base);
    return product.to_double();
}

std::uint32_t sha256_prefix(const std::string& input) {
    return sha256_first64(input) >> 32;
}

Groups quick_check(const Instance& instance, double p0, double seconds,
                   const std::filesystem::path& cache_directory, bool& timed_out) {
    timed_out = false;
    std::ostringstream probability;
    probability.imbue(std::locale::classic());
    probability << std::setprecision(12) << p0;
    const std::string descriptor = "v2|" + instance.name + "|m=" + std::to_string(instance.classes) +
        "|L=" + std::to_string(instance.sample_count) + "|p0=" + probability.str() + "|list=10|K=50";
    Groups rows;
    std::filesystem::path file;
    if (!cache_directory.empty()) {
        std::ostringstream digest;
        digest << std::hex << std::setfill('0') << std::setw(16) << sha256_first64(descriptor);
        const std::string safe = std::regex_replace(instance.name, std::regex("[^A-Za-z0-9_.-]+"), "_");
        file = cache_directory / (safe + "_p" + probability.str() + "_" + digest.str() + ".json");
        if (read_cache(file, instance, p0, rows)) return rows;
    }
    const auto deadline = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
    try {
        const auto seed = sha256_prefix("ddts-qc-" + descriptor);
        const auto build = [&] { return build_rows(instance.sample_count, instance.classes, p0, seed, deadline); };
        if (file.empty()) return build();
        std::filesystem::create_directories(cache_directory);
        CacheLock lock(file.string() + ".lock", deadline);
        if (read_cache(file, instance, p0, rows)) return rows;
        rows = build();
        write_cache(file, instance, p0, seed, rows);
        return rows;
    } catch (const QuickCheckTimeout&) {
        timed_out = true;
        return {};
    }
}

} // namespace ccmckp
