/* Deterministic, browser-native teaching model. No target data enters training. */
(function (root) {
  'use strict';
  const VERSION = '1.0.0';
  const SOURCE_COEFFICIENTS = [0.6, 1.2, 1.8];
  const TEMPERATURE = 0.02;
  const REGULARIZATION = 0.012;
  const sigmoid = x => x >= 0 ? 1 / (1 + Math.exp(-x)) : Math.exp(x) / (1 + Math.exp(x));
  const softplus = x => Math.max(0, x) + Math.log1p(Math.exp(-Math.abs(x)));

  function random(seed) {
    let state = seed >>> 0;
    return () => {
      state += 0x6D2B79F5;
      let t = Math.imul(state ^ state >>> 15, 1 | state);
      t ^= t + Math.imul(t ^ t >>> 7, 61 | t);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function makeLatents(n, seed) {
    const rng = random(seed);
    const rows = [];
    for (let i = 0; i < n; i++) {
      const r = Math.sqrt(-2 * Math.log(Math.max(1e-12, rng())));
      const angle = 2 * Math.PI * rng();
      rows.push([r * Math.cos(angle), r * Math.sin(angle), rng()]);
    }
    return rows;
  }

  function generate(options = {}) {
    const { n = 2400, seed = 20261026, covariate = 0, concept = 0,
      mechanismBreak = false, coefficient, latents = makeLatents(n, seed) } = options;
    if (![covariate, concept].every(Number.isFinite)) throw new TypeError('Shift must be finite');
    const promoCoefficient = coefficient ?? 1.2 - 3.6 * concept;
    const activeCoefficient = mechanismBreak ? 1.5 : -1.5;
    return latents.map(([u, v, coin]) => {
      // Only P(X) changes with covariate; P(Y|X) changes with concept.
      const x = u - 0.85 * covariate;
      const z = v * (1 + 0.25 * covariate) + 0.75 * covariate;
      const probability = sigmoid(activeCoefficient * x + promoCoefficient * z - 0.2);
      return { x, z, y: coin < probability ? 1 : 0, probability };
    });
  }

  function riskGradient(weights, rows) {
    let loss = 0, b = 0, x = 0, z = 0;
    for (const row of rows) {
      const score = weights[0] + weights[1] * row.x + weights[2] * row.z;
      loss += softplus(score) - row.y * score;
      const error = sigmoid(score) - row.y;
      b += error; x += error * row.x; z += error * row.z;
    }
    const n = rows.length;
    return { loss: loss / n, gradient: [b / n, x / n, z / n] };
  }

  function objective(weights, domains, robust = false) {
    const terms = domains.map(rows => riskGradient(weights, rows));
    let domainWeights;
    let dataLoss;
    if (robust) {
      const max = Math.max(...terms.map(t => t.loss));
      const exponentials = terms.map(t => Math.exp((t.loss - max) / TEMPERATURE));
      const sum = exponentials.reduce((a, b) => a + b, 0);
      domainWeights = exponentials.map(x => x / sum);
      dataLoss = max + TEMPERATURE * Math.log(sum);
    } else {
      domainWeights = terms.map(() => 1 / terms.length);
      dataLoss = terms.reduce((a, t) => a + t.loss, 0) / terms.length;
    }
    const gradient = [0, 0, 0];
    terms.forEach((term, i) => term.gradient.forEach((g, j) => { gradient[j] += domainWeights[i] * g; }));
    gradient[1] += REGULARIZATION * weights[1];
    gradient[2] += REGULARIZATION * weights[2];
    return {
      loss: dataLoss + REGULARIZATION * (weights[1] ** 2 + weights[2] ** 2) / 2,
      gradient, worstLoss: Math.max(...terms.map(t => t.loss)),
    };
  }

  function optimize(domains, robust) {
    let weights = [0, 0, 0];
    for (let iteration = 0; iteration < 620; iteration++) {
      const result = objective(weights, domains, robust);
      const step = 0.8 / (1 + 0.003 * iteration);
      weights = weights.map((w, j) => w - step * result.gradient[j]);
    }
    const result = objective(weights, domains, robust);
    return { weights, loss: result.loss, worstLoss: result.worstLoss,
      gradientNorm: Math.hypot(...result.gradient) };
  }

  function train({ radius = 0.65, seed = 615 } = {}) {
    if (!Number.isFinite(radius) || radius < 0 || radius > 1) throw new RangeError('Radius must be in [0,1]');
    // This function deliberately accepts no target configuration or target samples.
    const sourceDomains = SOURCE_COEFFICIENTS.map((coefficient, i) =>
      generate({ n: 420, seed: seed + i * 71, coefficient }));
    const coefficients = [0.6 - 2.8 * radius, 1.2, 1.8 + 0.6 * radius];
    const covariates = [-0.75 * radius, 0, 0.75 * radius];
    const uncertainDomains = [];
    for (let i = 0; i < coefficients.length; i++) {
      for (let j = 0; j < covariates.length; j++) {
        uncertainDomains.push(generate({ n: 420, seed: seed + 3000 + i * 71 + j * 503,
          coefficient: coefficients[i], covariate: covariates[j] }));
      }
    }
    const erm = optimize(sourceDomains, false);
    const dro = optimize([...sourceDomains, ...uncertainDomains], true);
    return { version: VERSION, seed, radius, erm, dro,
      sourceCoefficients: [...SOURCE_COEFFICIENTS],
      uncertainty: { promoMin: coefficients[0], promoMax: coefficients[2],
        covMin: covariates[0], covMax: covariates[2],
        temperature: TEMPERATURE, domains: 12,
        smoothingErrorBound: TEMPERATURE * Math.log(12) },
      sourceSampleCount: 1260, augmentedSampleCount: 3780,
    };
  }

  function predict(weights, rows) {
    return rows.map(row => sigmoid(weights[0] + weights[1] * row.x + weights[2] * row.z));
  }

  function auc(labels, scores) {
    if (labels.length !== scores.length || labels.length === 0) throw new RangeError('Invalid AUC input');
    const sorted = scores.map((score, i) => {
      if (!Number.isFinite(score) || ![0, 1].includes(labels[i])) throw new TypeError('Invalid AUC value');
      return { score, y: labels[i] };
    }).sort((a, b) => a.score - b.score);
    const positives = labels.reduce((a, b) => a + b, 0);
    const negatives = labels.length - positives;
    if (!positives || !negatives) return null;
    let positiveRanks = 0;
    for (let i = 0; i < sorted.length;) {
      let end = i + 1;
      while (end < sorted.length && sorted[end].score === sorted[i].score) end++;
      const averageRank = (i + 1 + end) / 2;
      for (let j = i; j < end; j++) positiveRanks += sorted[j].y * averageRank;
      i = end;
    }
    return (positiveRanks - positives * (positives + 1) / 2) / (positives * negatives);
  }

  function evaluate(model, rows) {
    const scores = predict(model.weights, rows);
    let loss = 0, correct = 0;
    rows.forEach((row, i) => {
      const p = Math.max(1e-12, Math.min(1 - 1e-12, scores[i]));
      loss -= row.y * Math.log(p) + (1 - row.y) * Math.log(1 - p);
      correct += Number((p >= 0.5 ? 1 : 0) === row.y);
    });
    return { auc: auc(rows.map(r => r.y), scores), logLoss: loss / rows.length,
      accuracy: correct / rows.length, churnRate: rows.reduce((s, r) => s + r.y, 0) / rows.length };
  }

  function assess(models, config = {}) {
    const { covariate = 0, concept = 0, mechanismBreak = false, seed = 20261026 } = config;
    const latents = makeLatents(2400, seed);
    const source = generate({ latents, concept: 0, covariate: 0 });
    const current = generate({ latents, covariate, concept, mechanismBreak });
    const curves = Array.from({ length: 17 }, (_, i) => {
      const strength = i / 16;
      const rows = generate({ latents, covariate, concept: strength, mechanismBreak });
      return { strength, erm: evaluate(models.erm, rows).auc, dro: evaluate(models.dro, rows).auc };
    });
    const grid = [];
    for (const c of [0, 0.33, 0.67, 1]) for (const k of [0, 0.33, 0.67, 1]) {
      const rows = generate({ latents, covariate: c, concept: k, mechanismBreak });
      grid.push({ covariate: c, concept: k, erm: evaluate(models.erm, rows).auc, dro: evaluate(models.dro, rows).auc });
    }
    const coefficient = 1.2 - 3.6 * concept;
    const u = models.uncertainty;
    const inside = !mechanismBreak && coefficient >= u.promoMin && coefficient <= u.promoMax
      && covariate >= u.covMin && covariate <= u.covMax;
    return { source: { erm: evaluate(models.erm, source), dro: evaluate(models.dro, source) },
      current: { erm: evaluate(models.erm, current), dro: evaluate(models.dro, current) },
      worst: { erm: Math.min(...grid.map(r => r.erm)), dro: Math.min(...grid.map(r => r.dro)) },
      curves, grid, inside, coefficient, points: current.slice(0, 360), sampleCount: current.length,
      sourcePoints: source.slice(0, 360),
    };
  }

  root.ShiftLab = { VERSION, TEMPERATURE, REGULARIZATION, sigmoid, softplus, random,
    makeLatents, generate, riskGradient, objective, train, predict, auc, evaluate, assess };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.ShiftLab;
})(typeof globalThis !== 'undefined' ? globalThis : this);
