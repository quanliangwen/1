#include "rng.hpp"
#include <cmath>

namespace ccmckp {

PythonRandom::PythonRandom(std::uint32_t seed) : PythonRandom(std::vector<std::uint32_t>{seed}) {}

PythonRandom::PythonRandom(const std::vector<std::uint32_t>& seed_words) {
    if (seed_words.empty()) throw std::invalid_argument("empty MT seed");
    state_[0] = 19650218u;
    for (std::size_t i = 1; i < state_.size(); ++i) {
        const auto previous = state_[i - 1];
        state_[i] = 1812433253u * (previous ^ (previous >> 30)) + i;
    }
    std::size_t i = 1;
    for (std::size_t step = 0; step < std::max(state_.size(), seed_words.size()); ++step) {
        const auto j = step % seed_words.size();
        const auto previous = state_[i - 1];
        state_[i] = (state_[i] ^ ((previous ^ (previous >> 30)) * 1664525u)) + seed_words[j] + j;
        if (++i == state_.size()) {
            state_[0] = state_.back();
            i = 1;
        }
    }
    for (std::size_t j = 1; j < state_.size(); ++j) {
        const auto previous = state_[i - 1];
        state_[i] = (state_[i] ^ ((previous ^ (previous >> 30)) * 1566083941u)) - i;
        if (++i == state_.size()) {
            state_[0] = state_.back();
            i = 1;
        }
    }
    state_[0] = 0x80000000u;
}

std::uint32_t PythonRandom::next() {
    if (position_ == state_.size()) {
        for (std::size_t i = 0; i < state_.size(); ++i) {
            const auto value = (state_[i] & 0x80000000u) |
                (state_[(i + 1) % state_.size()] & 0x7fffffffu);
            state_[i] = state_[(i + 397) % state_.size()] ^ (value >> 1) ^
                ((value & 1u) * 0x9908b0dfu);
        }
        position_ = 0;
    }
    auto value = state_[position_++];
    value ^= value >> 11;
    value ^= (value << 7) & 0x9d2c5680u;
    value ^= (value << 15) & 0xefc60000u;
    return value ^ (value >> 18);
}

std::uint32_t PythonRandom::below(std::uint32_t bound) {
    if (bound == 0) throw std::invalid_argument("empty Python choice");
    const int bits = 32 - __builtin_clz(bound);
    std::uint32_t value;
    do {
        value = next() >> (32 - bits);
    } while (value >= bound);
    return value;
}

Pcg64::Wide Pcg64::pack(std::uint64_t high, std::uint64_t low) {
    return (static_cast<Wide>(high) << 64) | low;
}

Pcg64::Pcg64(std::uint64_t seed) {
    std::vector<std::uint32_t> entropy{static_cast<std::uint32_t>(seed)};
    if (seed >> 32) entropy.push_back(seed >> 32);


    entropy.resize(4, 0);

    std::uint32_t hash = 0x43b0d7e5u;
    const auto hashmix = [&hash](std::uint32_t value) {
        value ^= hash;
        hash *= 0x931e8875u;
        value *= hash;
        return value ^ (value >> 16);
    };
    std::array<std::uint32_t, 4> pool{};
    for (std::size_t i = 0; i < pool.size(); ++i) pool[i] = hashmix(entropy[i]);
    for (std::size_t src = 0; src < pool.size(); ++src) {
        for (std::size_t dst = 0; dst < pool.size(); ++dst) {
            if (src == dst) continue;
            auto mixed = 0xca01f9ddu * pool[dst] - 0x4973f715u * hashmix(pool[src]);
            pool[dst] = mixed ^ (mixed >> 16);
        }
    }
    hash = 0x8b51f9ddu;
    std::array<std::uint64_t, 4> words{};
    for (std::size_t i = 0; i < 8; ++i) {
        auto value = pool[i % 4] ^ hash;
        hash *= 0x58f38dedu;
        value *= hash;
        value ^= value >> 16;
        words[i / 2] |= static_cast<std::uint64_t>(value) << (32 * (i % 2));
    }
    increment_ = (pack(words[2], words[3]) << 1) | 1;
    next64();
    state_ += pack(words[0], words[1]);
    next64();
}

std::uint64_t Pcg64::next64() {
    const auto multiplier = pack(2549297995355413924ULL, 4865540595714422341ULL);
    state_ = state_ * multiplier + increment_;
    const auto high = static_cast<std::uint64_t>(state_ >> 64);
    const auto mixed = high ^ static_cast<std::uint64_t>(state_);
    const auto rotate = high >> 58;
    return (mixed >> rotate) | (mixed << ((64 - rotate) % 64));
}

std::uint32_t Pcg64::next32() {
    if (has_spare_) {
        has_spare_ = false;
        return spare_;
    }
    const auto value = next64();
    spare_ = value >> 32;
    has_spare_ = true;
    return static_cast<std::uint32_t>(value);
}

std::uint32_t Pcg64::below(std::uint32_t bound) {
    if (bound <= 1) return 0;
    const std::uint32_t threshold = (0u - bound) % bound;
    std::uint64_t value;
    do {
        value = static_cast<std::uint64_t>(next32()) * bound;
    } while (static_cast<std::uint32_t>(value) < threshold);
    return value >> 32;
}

double LegacyRandom::uniform() {
    const std::uint32_t a = generator_() >> 5;
    const std::uint32_t b = generator_() >> 6;
    return (a * 67108864.0 + b) / 9007199254740992.0;
}

double LegacyRandom::normal() {
    if (has_normal_spare_) {
        has_normal_spare_ = false;
        return normal_spare_;
    }
    double x1, x2, r2;
    do {
        x1 = 2.0 * uniform() - 1.0;
        x2 = 2.0 * uniform() - 1.0;
        r2 = x1 * x1 + x2 * x2;
    } while (r2 >= 1.0 || r2 == 0.0);
    const double f = std::sqrt(-2.0 * std::log(r2) / r2);
    normal_spare_ = f * x1;
    has_normal_spare_ = true;
    return f * x2;
}

double LegacyRandom::gamma(double shape) {
    const auto exponential = [&] { return -std::log(1.0 - uniform()); };
    if (shape == 1.0) return exponential();
    if (shape == 0.0) return 0;
    if (shape < 1.0) {
        for (;;) {
            const double u = uniform(), v = exponential();
            if (u <= 1.0 - shape) {
                const double x = std::pow(u, 1.0 / shape);
                if (x <= v) return x;
            } else {
                const double y = -std::log((1 - u) / shape);
                const double x = std::pow(1.0 - shape + shape * y, 1.0 / shape);
                if (x <= v + y) return x;
            }
        }
    }
    const double b = shape - 1.0 / 3.0, c = 1.0 / std::sqrt(9 * b);
    for (;;) {
        double x, v;
        do {
            x = normal();
            v = 1.0 + c * x;
        } while (v <= 0.0);
        v = v * v * v;
        const double u = uniform();
        if (u < 1.0 - 0.0331 * (x * x) * (x * x) ||
            std::log(u) < 0.5 * x * x + b * (1.0 - v + std::log(v))) return b * v;
    }
}

std::uint32_t Pcg64::interval(std::uint32_t maximum) {
    if (!maximum) return 0;
    std::uint32_t mask = maximum;
    for (int shift = 1; shift < 32; shift <<= 1) mask |= mask >> shift;
    std::uint32_t value;
    do { value = next32() & mask; } while (value > maximum);
    return value;
}

std::vector<std::uint16_t> Pcg64::integers16(std::uint16_t bound, std::size_t count) {
    if (!bound) throw std::invalid_argument("Empty int16 RNG range");
    std::vector<std::uint16_t> result(count);
    if (bound == 1) return result;
    std::uint32_t buffer = 0;
    bool spare = false;
    const auto word = [&]() -> std::uint16_t {
        if (!spare) buffer = next32();
        spare = !spare;
        return static_cast<std::uint16_t>(spare ? buffer : buffer >> 16);
    };
    const std::uint32_t threshold = (65536u - bound) % bound;
    for (auto& x : result) {
        std::uint32_t value;
        do { value = std::uint32_t(word()) * bound; } while ((value & 65535u) < threshold);
        x = static_cast<std::uint16_t>(value >> 16);
    }
    return result;
}

} // namespace ccmckp
