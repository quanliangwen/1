"""Independent full positive convolutions and joint-mixture ambiguity checks."""
from pathlib import Path
import sys, json, hashlib
import numpy as np
H = Path(__file__).resolve().parent
I = H / 'iterations/I015_precision_closure'
sys.path[:0] = [str(I / 'candidate'), str(I / 'vendor313')]
from bootstrap_cdf_models_v1 import bootstrap_models, robust_gradients
from engine import worst_cdf_hist
D = H / 'research/bootstrap_ambiguity'
D.mkdir(exist_ok=True)
out = D / 'MATH_CHECK.json'
if out.exists():
    raise RuntimeError('No bootstrap math-check overwrite')
rng = np.random.default_rng(711016)
groups = [np.array([0, 3]), np.array([1, 4]), np.array([2, 5])]
center = [0, 1, 2]
samples = [np.r_[0., rng.uniform(0., 16., 8 + j), 10., 17.] for j in range(6)]
counts = dict(center=0, replacement=0, joint_mixture=0, nominal_counts=0)
maximum_error = 0.
def direct(histogram, q, bins):
    value = np.array([1.])
    for j in q:
        value = np.convolve(value, histogram[j])
    return float(value[:bins].sum())
for bins in [16, 32, 64]:
    for scenarios in [1, 4]:
        for seed in [711016, 711017]:
            models, overflow, metadata = bootstrap_models(samples, 10., bins, scenarios, seed)
            duplicate, duplicate_overflow, _ = bootstrap_models(samples, 10., bins, scenarios, seed)
            assert np.array_equal(models, duplicate) and np.array_equal(overflow, duplicate_overflow)
            assert np.allclose(models.sum(axis=2) + overflow, 1., atol=1e-14)
            for j, array in enumerate(samples):
                assert np.array_equal(models[0, j], worst_cdf_hist(array, 10., bins, 0.))
                assert sum(metadata['empirical_counts_with_overflow'][j]) == len(array)
                counts['nominal_counts'] += 1
            worst, ps, weights = robust_gradients(groups, models, center)
            assert worst == float(ps.min()) and worst <= ps[0]
            for k, hist in enumerate(models):
                error = abs(ps[k] - direct(hist, center, bins))
                maximum_error = max(maximum_error, error)
                assert error < 1e-11
                counts['center'] += 1
                for g, items in enumerate(groups):
                    for j in items:
                        q = center.copy()
                        q[g] = int(j)
                        error = abs(ps[k] + weights[k, j] - direct(hist, q, bins))
                        maximum_error = max(maximum_error, error)
                        assert error < 1e-11
                        counts['replacement'] += 1
            for g, items in enumerate(groups):
                for j in items:
                    q = center.copy()
                    q[g] = int(j)
                    assert abs(np.min(ps + weights[:, j]) - min(direct(hist, q, bins) for hist in models)) < 1e-11

# Full joint tables distinguish mixtures of product models from products of
# mixed marginals; only the former is the proposed finite ambiguity set.
models, overflow, _ = bootstrap_models([np.array([0., 1., 3.]), np.array([0., 2., 4.])], 3., 4, 4, 51)
full = np.concatenate([models, overflow[:, :, None]], axis=2)
vertices = np.array([np.outer(hist[0], hist[1]) for hist in full])
event = np.add.outer(np.arange(5), np.arange(5)) < 4
values = vertices[:, event].sum(axis=1)
minimum = values.min()
for alpha in list(np.eye(5)) + [rng.dirichlet(np.ones(5)) for _ in range(100)]:
    joint = np.tensordot(alpha, vertices, axes=1)
    value = float(joint[event].sum())
    assert abs(value - alpha @ values) < 1e-12 and minimum - 1e-12 <= value <= values.max() + 1e-12
    counts['joint_mixture'] += 1
both_low = np.outer([1., 0., 0.], [1., 0., 0.])
both_high = np.outer([0., 0., 1.], [0., 0., 1.])
event2 = np.add.outer(np.arange(3), np.arange(3)) < 2
joint_mixture = .5 * both_low + .5 * both_high
product_marginal_mix = np.outer([.5, 0., .5], [.5, 0., .5])
assert joint_mixture[event2].sum() == .5 and product_marginal_mix[event2].sum() == .25
tail_models, tail_overflow, _ = bootstrap_models([np.array([0., 1.])], 1., 8, 64, 99)
assert tail_overflow[0, 0] == .5 and tail_models[0, 0].sum() == .5
assert 0. in tail_overflow[:, 0] and 1. in tail_overflow[:, 0]
invalid = [([], 1., 8, 1), ([np.array([])], 1., 8, 1), ([np.array([-1.])], 1., 8, 1),
           ([np.array([np.nan])], 1., 8, 1), ([np.array([0.])], 0., 8, 1),
           ([np.array([0.])], 1., 1, 1), ([np.array([0.])], 1., 8, 0)]
for args in invalid:
    try:
        bootstrap_models(*args, seed=0)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid model accepted')
result = dict(passed=True, checks=counts, maximum_absolute_CDF_error=maximum_error,
    deterministic_resampling=True, overflow_category_preserved=True,
    joint_ambiguity_not_product_of_marginal_mixtures=True,
    invalid_models_rejected=len(invalid), new_MC_calls=0,
    scope='finite-grid bootstrap JOINT model ambiguity and single-group proposal derivatives versus independent full positive convolution; no raw feasibility/real probability or optimizer performance claim',
    source_sha256={name: hashlib.sha256((H / name).read_bytes()).hexdigest() for name in ['bootstrap_cdf_models_v1.py', 'check_bootstrap_cdf_models.py']},
    unchanged_base_source_sha256={name: hashlib.sha256((I / 'candidate' / name).read_bytes()).hexdigest() for name in ['engine.py', 'portfolio_lns.py']}, numpy=np.__version__)
with out.open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
