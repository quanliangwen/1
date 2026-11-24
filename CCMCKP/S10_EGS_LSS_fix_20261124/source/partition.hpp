#pragma once
#include <algorithm>
#include <numeric>
#include <vector>

namespace s10 {
// NumPy 1.24 indirect introselect for finite values and -infinity.
// Adapted from numpy/core/src/npysort/selection.cpp, see LICENSE_NUMPY.txt.
inline void partition_indices(const std::vector<double>& scores, int* ids, int size, int kth) {
    const auto value = [&](int i) { return scores[ids[i]]; };
    const auto order_pair = [&](int a, int b) { if (value(b) < value(a)) std::swap(ids[a], ids[b]); };
    if (kth < 3) {
        for (int i = 0; i <= kth; ++i) {
            int smallest = i;
            for (int j = i + 1; j < size; ++j)
                if (value(j) < value(smallest)) smallest = j;
            std::swap(ids[i], ids[smallest]);
        }
        return;
    }
    if (kth == size - 1) {
        int largest = 0;
        for (int i = 1; i < size; ++i)
            if (value(i) >= value(largest)) largest = i;
        std::swap(ids[kth], ids[largest]);
        return;
    }
    int depth = 0;
    for (int n = size; n > 1; n >>= 1) depth += 2;
    int low = 0, high = size - 1;
    while (low + 1 < high) {
        int left = low + 1, right = high;
        if (depth > 0 || right - left < 5) {
            const int mid = low + (high - low) / 2;
            order_pair(mid, high);
            order_pair(low, high);
            order_pair(mid, low);
            std::swap(ids[mid], ids[low + 1]);
        } else {
            const int count = (right - left) / 5;
            for (int k = 0; k < count; ++k) {
                const int first = left + 5 * k;
                order_pair(first, first + 1);
                order_pair(first + 3, first + 4);
                order_pair(first, first + 3);
                order_pair(first + 1, first + 4);
                order_pair(first + 1, first + 2);
                int median = first + 2;
                if (value(first + 3) < value(first + 2))
                    median = first + (value(first + 3) < value(first + 1) ? 1 : 3);
                std::swap(ids[median], ids[left + k]);
            }
            if (count > 2) partition_indices(scores, ids + left, count, count / 2);
            std::swap(ids[left + count / 2], ids[low]);
            --left;
            ++right;
        }
        --depth;
        const double pivot = value(low);
        for (;;) {
            do { ++left; } while (value(left) < pivot);
            do { --right; } while (pivot < value(right));
            if (right < left) break;
            std::swap(ids[left], ids[right]);
        }
        std::swap(ids[low], ids[right]);
        if (right >= kth) high = right - 1;
        if (right <= kth) low = left;
    }
    if (high == low + 1) order_pair(low, high);
}
} // namespace s10
