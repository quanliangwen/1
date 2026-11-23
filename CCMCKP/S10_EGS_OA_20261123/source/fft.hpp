#pragma once
#define POCKETFFT_NO_MULTITHREADING
#define POCKETFFT_CACHE_SIZE 16
#include <pocketfft_hdronly.h>
#include <algorithm>
#include <complex>
#include <vector>

namespace s10 {
template <class T> using Freq = std::vector<std::complex<T>>;

template <class T>
Freq<T> forward(const std::vector<T>& row) {
    const std::size_t b = row.size();
    std::vector<T> input(2 * b);
    std::copy(row.begin(), row.end(), input.begin());
    Freq<T> out(b + 1);
    pocketfft::r2c({2 * b}, {sizeof(T)}, {sizeof(std::complex<T>)}, 0,
                  true, input.data(), out.data(), T(1));
    return out;
}

template <class T>
std::vector<T> inverse(const Freq<T>& freq, bool clip) {
    const std::size_t b = freq.size() - 1;
    std::vector<T> out(2 * b);
    pocketfft::c2r({2 * b}, {sizeof(std::complex<T>)}, {sizeof(T)}, 0,
                  false, freq.data(), out.data(), T(1) / T(2 * b));
    out.resize(b);
    if (clip)
        for (T& v : out) v = std::max(T(0), v);
    return out;
}

template <class T>
void multiply(Freq<T>& left, const Freq<T>& right) {
    for (std::size_t k = 0; k < left.size(); ++k) left[k] *= right[k];
}

template <class T>
std::vector<T> convolve(const std::vector<T>& left, const std::vector<T>& right) {
    auto product = forward(left);
    multiply(product, forward(right));
    return inverse(product, true);
}
} // namespace s10
