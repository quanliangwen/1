const test = require('node:test');
const assert = require('node:assert/strict');
const L = require('./model.js');

test('AUROC handles perfect, reversed and tied predictions', () => {
  assert.equal(L.auc([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8]), 1);
  assert.equal(L.auc([0, 1, 0, 1], [0.9, 0.1, 0.8, 0.2]), 0);
  assert.equal(L.auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]), 0.5);
  assert.equal(L.auc([0, 0], [0.1, 0.2]), null);
  assert.throws(() => L.auc([1], []));
});

test('covariate-only shift preserves the conditional label rule', () => {
  const rows = L.generate({ covariate: 0.8, concept: 0, n: 30 });
  for (const r of rows) assert.ok(Math.abs(r.probability - L.sigmoid(-1.5 * r.x + 1.2 * r.z - 0.2)) < 1e-12);
});

test('concept-only shift leaves the input samples exactly unchanged', () => {
  const a = L.generate({ concept: 0, n: 80 });
  const b = L.generate({ concept: 0.8, n: 80 });
  assert.deepEqual(a.map(r => [r.x, r.z]), b.map(r => [r.x, r.z]));
  assert.ok(a.some((r, i) => r.y !== b[i].y));
});

test('the robust loss gradient agrees with finite differences', () => {
  const ds = [L.generate({ n: 80, seed: 1 }), L.generate({ n: 80, seed: 2, concept: 0.7 })];
  const w = [0.1, -0.3, 0.4];
  for (const robust of [false, true]) {
    const gradient = L.objective(w, ds, robust).gradient;
    w.forEach((_, j) => {
      const lo = [...w], hi = [...w]; lo[j] -= 1e-5; hi[j] += 1e-5;
      const numerical = (L.objective(hi, ds, robust).loss - L.objective(lo, ds, robust).loss) / 2e-5;
      assert.ok(Math.abs(numerical - gradient[j]) < 1e-6);
    });
  }
});

test('training is deterministic, converges, and ignores target configuration', () => {
  const a = L.train({ radius: 0.65 });
  const b = L.train({ radius: 0.65, covariate: 1, concept: 1, mechanismBreak: true });
  assert.deepEqual(a, b);
  assert.ok(a.erm.gradientNorm < 0.002);
  assert.ok(a.dro.gradientNorm < 0.002);
  assert.ok(Math.abs(a.dro.weights[2]) < Math.abs(a.erm.weights[2]));
  const before = JSON.stringify(a);
  const result = L.assess(a, { concept: 0.65, covariate: 0.4 });
  assert.equal(JSON.stringify(a), before, 'test evaluation must not modify the trained model');
  for (const model of ['erm', 'dro']) {
    assert.ok(result.current[model].auc > 0 && result.current[model].auc < 1);
    assert.ok(result.current[model].logLoss > 0);
  }
});

test('unprotected mechanism changes are outside the declared uncertainty scope', () => {
  const m = L.train();
  assert.equal(L.assess(m, {}).inside, true);
  assert.equal(L.assess(m, { mechanismBreak: true }).inside, false);
});
