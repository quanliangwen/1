#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <random>
#include <stdexcept>
#include <vector>

namespace ccmckp {

// NumPy 1.24 RandomState uses masked rejection and reverse Fisher-Yates.
class LegacyRandom {
public:
    explicit LegacyRandom(std::uint32_t seed) : generator_(seed) {}

    std::uint32_t below(std::uint32_t bound) {
        if (bound <= 1) return 0;
        const std::uint32_t limit = bound - 1;
        auto mask = limit;
        mask |= mask >> 1;
        mask |= mask >> 2;
        mask |= mask >> 4;
        mask |= mask >> 8;
        mask |= mask >> 16;
        std::uint32_t value;
        do {
            value = generator_() & mask;
        } while (value > limit);
        return value;
    }

    template <class T>
    void shuffle(std::vector<T>& values) {
        for (std::size_t size = values.size(); size > 1; --size) {
            std::swap(values[size - 1], values[below(size)]);
        }
    }

private:
    std::mt19937 generator_;
};

// CPython 3.8 random.seed(int) uses MT init_by_array with one seed word.
// Its choice() takes the high getrandbits bits and rejects out-of-range values.
class PythonRandom {
public:
    explicit PythonRandom(std::uint32_t seed);
    explicit PythonRandom(const std::vector<std::uint32_t>& seed_words);
    std::uint32_t below(std::uint32_t bound);
private:
    std::uint32_t next();
    std::array<std::uint32_t, 624> state_{};
    std::size_t position_ = 624;
};

// NumPy SeedSequence and PCG64. See THIRD_PARTY_NOTICES.txt.
class PilotRandom {
public:
    PilotRandom(std::uint64_t seed, std::uint32_t group, std::uint32_t salt);
    std::uint32_t below(std::uint32_t bound);
private:
    using Wide = __uint128_t;
    static Wide pack(std::uint64_t high, std::uint64_t low);
    std::uint64_t next64();
    std::uint32_t next32();
    Wide state_ = 0;
    Wide increment_ = 0;
    std::uint32_t spare_ = 0;
    bool has_spare_ = false;
};

} // namespace ccmckp
