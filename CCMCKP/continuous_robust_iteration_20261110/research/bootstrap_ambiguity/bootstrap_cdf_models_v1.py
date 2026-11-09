"""Finite joint-model ambiguity for proposal scores, never an acceptance gate.

Each vertex is a product of resampled empirical marginal histograms.  The
ambiguity set is the convex hull of these JOINT distributions.  Event
probability is linear in their mixture, so its minimum is a vertex minimum.
"""
import numpy as np
from engine import worst_cdf_hist
from portfolio_lns import cdf_gradients


def bootstrap_models(samples, capacity, bins, scenarios, seed):
    if not np.isfinite(capacity) or capacity <= 0 or not isinstance(bins, int) or bins < 2:
        raise ValueError('Positive capacity and integer grid required')
    if not isinstance(scenarios, int) or scenarios < 1 or not samples:
        raise ValueError('Nonempty marginals and positive scenario count required')
    arrays = [np.asarray(a, dtype=float) for a in samples]
    if any(a.ndim != 1 or not len(a) or np.any(~np.isfinite(a)) or np.any(a < 0) for a in arrays):
        raise ValueError('Finite nonnegative nonempty one-dimensional observations required')
    models = np.empty((scenarios + 1, len(arrays), bins), dtype=float)
    overflow = np.empty((scenarios + 1, len(arrays)), dtype=float)
    sizes = []
    counts = []
    rng = np.random.default_rng(seed)
    for j, array in enumerate(arrays):
        size = len(array)
        nominal = worst_cdf_hist(array, capacity, bins, 0.)
        observed = np.rint(nominal * size).astype(np.int64)
        if np.any(observed < 0) or observed.sum() > size or np.max(np.abs(observed - nominal * size)) > 1e-8:
            raise ArithmeticError('Nominal guidance histogram does not encode empirical counts')
        full_counts = np.r_[observed, size - observed.sum()]
        original_bins = np.repeat(np.arange(bins + 1), full_counts)
        models[0, j] = observed / size
        overflow[0, j] = full_counts[-1] / size
        sizes.append(size)
        counts.append(full_counts.tolist())
        for k in range(1, scenarios + 1):
            # Resample all original atoms, including the overflow category.
            chosen = original_bins[rng.integers(0, size, size=size)]
            resampled = np.bincount(chosen, minlength=bins + 1)
            models[k, j] = resampled[:-1] / size
            overflow[k, j] = resampled[-1] / size
    return models, overflow, dict(seed=int(seed), bins=bins, bootstrap_scenarios=scenarios,
        sizes=sizes, empirical_counts_with_overflow=counts,
        ambiguity='convex hull of nominal and bootstrap joint product models',
        score_role='proposal guidance only; original raw99 and original-LSS985 acceptance unchanged')


def robust_gradients(groups, models, selection):
    probabilities = []
    weights = []
    for histogram in models:
        p, w = cdf_gradients(groups, histogram, selection)
        probabilities.append(p)
        weights.append(w)
    probabilities = np.asarray(probabilities)
    return float(probabilities.min()), probabilities, np.asarray(weights)
