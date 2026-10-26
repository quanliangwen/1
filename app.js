(function () {
  'use strict';
  const L = window.ShiftLab;
  const $ = id => document.getElementById(id);
  const state = { phase: 0, radius: 0.65, frozen: false, busy: false, models: null,
    result: null, covariate: 0, concept: 0, mechanismBreak: false, vote: null,
    round: 0, seed: 20261026, trainingId: 0, presentation: false };
  const modelCache = new Map();
  let evaluationTimer;
  let activeWorker;
  const fmt = x => Number.isFinite(x) ? x.toFixed(3) : '不可计算';
  const percent = x => `${Math.round(x * 100)}%`;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const line = (x1, y1, x2, y2, attrs = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${attrs}/>`;
  const txt = (x, y, content, attrs = '') => `<text x="${x}" y="${y}" ${attrs}>${escape(content)}</text>`;
  function setText(id, value) { $(id).textContent = value; }

  function trainInWorker(config) {
    if (!window.Worker || location.protocol === 'file:') return Promise.resolve().then(() => L.train(config));
    return new Promise(resolve => {
      let settled = false;
      const worker = new Worker('./worker.js');
      activeWorker = worker;
      const finish = result => {
        if (settled) return;
        settled = true; clearTimeout(timeout); worker.terminate();
        if (activeWorker === worker) activeWorker = null;
        resolve(result);
      };
      const fallback = () => finish(L.train(config));
      const timeout = setTimeout(fallback, 5000);
      worker.onmessage = e => e.data.error ? fallback() : finish(e.data.result);
      worker.onerror = e => { e.preventDefault(); fallback(); };
      worker.postMessage({ id: state.trainingId, config });
    });
  }

  async function trainModels() {
    const id = ++state.trainingId;
    state.busy = true;
    $('results-panel').setAttribute('aria-busy', 'true');
    $('error-message').hidden = true;
    setText('model-status', '源域训练中');
    renderControls();
    try {
      const key = state.radius.toFixed(2);
      const result = modelCache.get(key) || await trainInWorker({ radius: state.radius, seed: 615 });
      if (id !== state.trainingId) return;
      modelCache.set(key, result);
      state.models = result;
      state.busy = false;
      assess();
    } catch (error) {
      state.busy = false;
      $('error-message').hidden = false;
      setText('error-message', `模型计算失败，请刷新后重试。${error.message}`);
      setText('model-status', '计算失败');
      renderControls();
    }
  }

  function assess() {
    if (!state.models || state.busy) return;
    try {
      state.result = L.assess(state.models, { covariate: state.covariate, concept: state.concept,
        mechanismBreak: state.mechanismBreak, seed: state.seed });
      $('results-panel').setAttribute('aria-busy', 'false');
      render();
    } catch (error) {
      $('error-message').hidden = false;
      setText('error-message', `评价计算失败：${error.message}`);
    }
  }

  function renderControls() {
    const revealed = state.phase >= 2;
    $('radius').disabled = state.frozen;
    $('radius').value = state.radius;
    setText('radius-value', state.radius.toFixed(2));
    $('covariate').disabled = !revealed || state.busy;
    $('concept').disabled = !revealed || state.busy;
    $('covariate').value = state.covariate;
    $('concept').value = state.concept;
    setText('covariate-value', percent(state.covariate));
    setText('concept-value', percent(state.concept));
    document.querySelectorAll('[data-preset]').forEach(button => { button.disabled = !revealed || state.busy; });
    document.querySelectorAll('[data-phase]').forEach(button => {
      const phase = Number(button.dataset.phase);
      button.classList.toggle('active', phase === state.phase);
      button.classList.toggle('complete', phase < state.phase);
      button.disabled = state.busy;
      if (phase === state.phase) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    $('break-control').hidden = state.phase !== 3;
    $('mechanism-break').checked = state.mechanismBreak;
    $('vote-panel').hidden = state.phase !== 1;
    $('curve-cover').hidden = revealed;
    $('next').disabled = state.busy || !state.models;
    $('export').disabled = state.busy || !state.result;
    if (!state.busy) setText('model-status', state.frozen ? '模型已冻结' : '训练完成');
    setText('lock-note', state.frozen ? '已冻结。调整测试环境不会触发重新训练。' : '揭晓测试环境前，可修改并重新训练。');
    setText('environment-lock', revealed ? '仅改变测试环境' : '待揭晓');
    const labels = ['冻结模型，做出判断', '揭晓新环境', '检查保护边界', '回到原环境对比'];
    $('next').innerHTML = `${state.busy ? '准备模型中…' : labels[state.phase]} <span aria-hidden="true">→</span>`;
  }

  function renderMetrics() {
    const revealed = state.phase >= 2;
    const result = revealed ? state.result.current : state.result.source;
    const delta = result.dro.auc - result.erm.auc;
    setText('erm-auc', fmt(result.erm.auc));
    setText('dro-auc', fmt(result.dro.auc));
    setText('auc-delta', `${delta >= 0 ? '+' : ''}${fmt(delta)}`);
    setText('erm-detail', revealed ? `同环境留出 ${fmt(state.result.source.erm.auc)} · 当前对数损失 ${fmt(result.erm.logLoss)}` : '同环境留出 AUROC · 不等于上线保证');
    setText('dro-detail', revealed ? `同环境留出 ${fmt(state.result.source.dro.auc)} · 当前对数损失 ${fmt(result.dro.logLoss)}` : '同环境留出 AUROC · 允许存在稳健代价');
    setText('delta-detail', delta >= 0 ? '本情景 DRO 高于 ERM' : '本情景 ERM 高于 DRO');
    setText('result-heading', !revealed ? '原环境里的好成绩' : state.mechanismBreak ? '当稳定机制也被打破' : '新环境，还是同一个模型');
    setText('context-indicator', !revealed ? 'SOURCE ENVIRONMENT' : state.mechanismBreak ? 'BEYOND THE ASSUMPTIONS' : 'UNSEEN ENVIRONMENT');
    setText('sample-note', `2,400 个独立模拟样本 · 第 ${state.round + 1} 轮`);
    setText('scatter-heading', revealed ? '新环境中的模拟客户' : '同环境留出样本');
    if (revealed) {
      setText('curve-caption', `当前客户构成 ${percent(state.covariate)} · 关系系数 b = ${state.result.coefficient.toFixed(2)}`);
      setText('grid-foot', `4×4 压力网格最低 AUROC：ERM ${fmt(state.result.worst.erm)} / DRO ${fmt(state.result.worst.dro)}`);
    } else {
      setText('curve-caption', '揭晓后查看性能随关系偏移的变化');
      setText('grid-foot', '压力测试：固定客户构成，逐步改变预测关系。');
    }
  }

  function renderScatter() {
    const points = state.phase >= 2 ? state.result.points : state.result.sourcePoints;
    const W = 470, H = 300, left = 43, right = 16, top = 20, bottom = 43;
    const minX = Math.min(-3.5, ...points.map(p => p.x - 0.1));
    const maxX = Math.max(3.5, ...points.map(p => p.x + 0.1));
    const minZ = Math.min(-3.5, ...points.map(p => p.z - 0.1));
    const maxZ = Math.max(3.5, ...points.map(p => p.z + 0.1));
    const sx = x => left + (x - minX) / (maxX - minX) * (W - left - right);
    const sy = z => H - bottom - (z - minZ) / (maxZ - minZ) * (H - top - bottom);
    let svg = `<defs><clipPath id="scatter-clip"><rect x="${left}" y="${top}" width="${W-left-right}" height="${H-top-bottom}"/></clipPath></defs>`;
    for (const tick of [-3, -1.5, 0, 1.5, 3]) {
      svg += line(sx(tick), top, sx(tick), H-bottom, 'class="chart-gridline"');
      svg += line(left, sy(tick), W-right, sy(tick), 'class="chart-gridline"');
      svg += txt(sx(tick), H-bottom+16, tick.toFixed(1), 'text-anchor="middle" class="chart-tick"');
      svg += txt(left-8, sy(tick)+3, tick.toFixed(1), 'text-anchor="end" class="chart-tick"');
    }
    svg += `<g clip-path="url(#scatter-clip)">`;
    svg += points.map(p => `<circle cx="${sx(p.x).toFixed(2)}" cy="${sy(p.z).toFixed(2)}" r="2.8" fill="${p.y ? '#cf8a7a' : '#79a89c'}" fill-opacity=".64"><title>活跃度 ${p.x.toFixed(2)}；促销接触度 ${p.z.toFixed(2)}；${p.y ? '流失' : '留存'}</title></circle>`).join('');
    for (const [key, color, dash] of [['erm','#cb744d',''], ['dro','#5268a8','stroke-dasharray="6 4"']]) {
      const w = state.models[key].weights;
      const x1 = -(w[0] + w[2] * minZ) / w[1];
      const x2 = -(w[0] + w[2] * maxZ) / w[1];
      svg += line(sx(x1), sy(minZ), sx(x2), sy(maxZ), `stroke="${color}" stroke-width="2.3" ${dash}`);
    }
    svg += '</g>';
    svg += line(left, H-bottom, W-right, H-bottom, 'class="chart-axis"');
    svg += txt((W+left-right)/2, H-5, '客户活跃度（标准化）', 'class="chart-label" text-anchor="middle"');
    svg += txt(left, 10, '促销接触度', 'class="chart-label"');
    $('scatter-chart').innerHTML = svg;
    $('scatter-chart').setAttribute('aria-label', `${state.phase >= 2 ? '新环境' : '同环境'}的 360 位模拟客户，橙色和蓝色线为 ERM 与 DRO 冻结后的分类边界`);
  }

  function renderCurve() {
    const revealed = state.phase >= 2;
    const W = 450, H = 300, left = 43, right = 28, top = 20, bottom = 43;
    const sx = x => left + x * (W-left-right);
    const sy = y => H-bottom-y*(H-top-bottom);
    let svg = '';
    if (revealed && !state.mechanismBreak && state.covariate <= state.models.uncertainty.covMax) {
      const edge = Math.min(1, Math.max(0, (1.2-state.models.uncertainty.promoMin)/3.6));
      svg += `<rect x="${left}" y="${top}" width="${sx(edge)-left}" height="${H-top-bottom}" fill="#f0f5e9"/>`;
      svg += txt(left+6, top+12, '训练情景的参数包络', 'class="chart-tick"');
    }
    for (const tick of [0, .25, .5, .75, 1]) {
      svg += line(left, sy(tick), W-right, sy(tick), 'class="chart-gridline"');
      svg += txt(left-8, sy(tick)+3, tick.toFixed(2), 'text-anchor="end" class="chart-tick"');
      svg += txt(sx(tick), H-bottom+16, percent(tick), 'text-anchor="middle" class="chart-tick"');
    }
    svg += line(left, sy(.5), W-right, sy(.5), 'stroke="#cbd4c2" stroke-dasharray="4 4"');
    svg += txt(W-right-2, sy(.5)-6, '随机排序参考 0.50', 'text-anchor="end" class="chart-tick"');
    if (revealed) {
      for (const [key,color] of [['erm','#cb744d'],['dro','#5268a8']]) {
        const path = state.result.curves.map((p,i) => `${i ? 'L' : 'M'}${sx(p.strength).toFixed(2)},${sy(p[key]).toFixed(2)}`).join(' ');
        svg += `<path d="${path}" stroke="${color}" stroke-width="2.8" fill="none" stroke-linejoin="round"/>`;
      }
      svg += line(sx(state.concept), top, sx(state.concept), H-bottom, 'stroke="#aeb8a3" stroke-width="1" stroke-dasharray="3 4"');
      for (const [key,color] of [['erm','#cb744d'],['dro','#5268a8']]) {
        const score = state.result.current[key].auc;
        svg += `<circle cx="${sx(state.concept)}" cy="${sy(score)}" r="4" fill="white" stroke="${color}" stroke-width="2"/>`;
      }
      svg += txt(W-right-5, top+12, 'ERM', 'text-anchor="end" fill="#cb744d" class="curve-label"');
      svg += txt(W-right-5, top+29, '情景 DRO', 'text-anchor="end" fill="#5268a8" class="curve-label"');
    }
    svg += line(left, H-bottom, W-right, H-bottom, 'class="chart-axis"');
    svg += txt((W+left-right)/2, H-5, '预测关系变化强度', 'class="chart-label" text-anchor="middle"');
    svg += txt(left, 10, 'AUROC', 'class="chart-tick"');
    $('curve-chart').innerHTML = svg;
    $('curve-chart').setAttribute('aria-label', revealed ? `预测关系逐渐改变时的性能曲线。当前 ERM ${fmt(state.result.current.erm.auc)}，DRO ${fmt(state.result.current.dro.auc)}` : '未来环境尚未揭晓');
  }

  function renderInsight() {
    let title, text, warning = false;
    if (state.phase === 0) {
      title = '让模型为变化做准备。';
      text = '相同的逻辑回归，两个训练目标。先选防护范围，观察同环境表现的代价，再冻结模型。';
    } else if (state.phase === 1) {
      title = '历史验证成绩，足以支持上线吗？';
      text = '这两项 AUROC 都来自独立的同环境留出样本。目标环境仍不可见，请先给出你的判断。';
    } else if (state.mechanismBreak) {
      title = '保护范围之外，稳健模型也会失准。';
      text = '活跃度与流失的关系也被反转，这不在预设训练情景内。比较实际指标，回到“假设是否合理”这个问题。';
      warning = true;
    } else if (state.phase === 3 && !state.result.inside) {
      title = '这个新环境，已经超出训练情景的参数包络。';
      text = '超出包络不意味着一定失败，落在包络内也不是连续分布保证。这里显示的是有限样本、有限情景的测试结果。';
      warning = true;
    } else if (state.concept === 0 && state.covariate === 0) {
      title = '新环境尚未变化，先从一个情景开始。';
      text = '点击“客户变了”“关系变了”或“同时变化”，也可以拖动滑块。模型参数保持冻结。';
    } else if (state.concept > 0 && state.covariate > 0) {
      title = '客户与预测关系同时变化，是更贴近业务的挑战。';
      text = '两条曲线来自实际评价。稳健训练减少对特定促销关联的依赖，但改善幅度取决于训练情景与真实变化是否匹配。';
    } else if (state.concept > 0) {
      title = state.concept > 1/3 ? '同样的客户特征，促销关联已经反转。' : '输入没变，预测关系开始变化。';
      text = '这次只改变 P(Y|X)，原有客户输入保持不变。过去有效的关联，未必继续适用于新环境。';
    } else {
      title = '客户构成变了，条件预测规则暂时没变。';
      text = '这次只改变 P(X)。分布变化不必然导致所有指标下降，是否受损需要实际检验，不能由“检测到漂移”直接推断。';
    }
    setText('insight-title', title); setText('insight-text', text);
    setText('insight-index', String(state.phase+1).padStart(2,'0'));
    $('insight').classList.toggle('warning', warning);
  }

  function render() {
    renderControls(); renderMetrics(); renderScatter(); renderCurve(); renderInsight();
    const presets = { covariate: [0.8,0], concept: [0,0.65], mixed: [0.5,0.6] };
    document.querySelectorAll('[data-preset]').forEach(button => {
      const [c,k] = presets[button.dataset.preset];
      button.classList.toggle('active', state.phase >= 2 && c === state.covariate && k === state.concept && !state.mechanismBreak);
    });
    document.documentElement.dataset.ready = 'true';
    document.dispatchEvent(new CustomEvent('shiftlab:updated', { detail: { phase: state.phase } }));
  }

  function goToPhase(phase) {
    if (state.busy || !state.models) return;
    state.phase = Math.max(0, Math.min(3, phase));
    if (phase >= 1) state.frozen = true;
    if (phase < 3) state.mechanismBreak = false;
    assess();
  }

  function advance() {
    if (state.phase < 3) goToPhase(state.phase+1);
    else {
      state.covariate = 0; state.concept = 0; state.mechanismBreak = false;
      goToPhase(2);
    }
  }

  function reset() {
    clearTimeout(evaluationTimer);
    state.phase = 0; state.frozen = false; state.vote = null;
    state.covariate = 0; state.concept = 0; state.mechanismBreak = false;
    state.round++; state.seed = 20261026 + state.round * 1000;
    trainModels();
  }

  function exportResult() {
    if (!state.result) return;
    const report = { title: '未见之变 · 教学模拟结果', version: L.VERSION,
      disclosure: '合成数据与平滑有限情景 DRO 教学实现，并非 Duan 等 (2026) 论文复现。压力网格最低 AUROC 不等于所有分布的最坏风险。',
      phase: state.phase, vote: state.vote, modelFrozen: state.frozen,
      evaluationSeed: state.seed, round: state.round+1,
      scenario: { covariate: state.covariate, concept: state.concept, mechanismBreak: state.mechanismBreak },
      models: state.models,
      sourceEvaluation: state.result.source,
      // Do not reveal target scores in a pre-reveal export.
      targetEvaluation: state.phase >= 2 ? state.result.current : null,
      grid: state.phase >= 2 ? state.result.grid : null,
      curves: state.phase >= 2 ? state.result.curves : null,
      paper: 'https://doi.org/10.1287/isre.2022.0537' };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `shift-lab-round-${state.round+1}.json`;
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  $('radius').addEventListener('input', event => {
    if (state.frozen) return;
    state.radius = Number(event.target.value);
    setText('radius-value', state.radius.toFixed(2));
    state.busy = true; renderControls(); setText('model-status', '等待重新训练');
  });
  $('radius').addEventListener('change', () => { if (!state.frozen) trainModels(); });
  for (const id of ['covariate','concept']) $(id).addEventListener('input', event => {
    if (state.phase < 2 || state.busy) return;
    state[id] = Number(event.target.value);
    setText(id+'-value', percent(state[id]));
    clearTimeout(evaluationTimer); evaluationTimer = setTimeout(assess, 60);
  });
  document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => {
    if (state.phase < 2 || state.busy) return;
    const presets = { covariate: [0.8,0], concept: [0,0.65], mixed: [0.5,0.6] };
    [state.covariate,state.concept] = presets[button.dataset.preset];
    state.mechanismBreak = false; assess();
  }));
  document.querySelectorAll('[data-phase]').forEach(button => button.addEventListener('click', () => goToPhase(Number(button.dataset.phase))));
  document.querySelectorAll('[data-vote]').forEach(button => button.addEventListener('click', () => { state.vote = button.dataset.vote; goToPhase(2); }));
  $('mechanism-break').addEventListener('change', event => { state.mechanismBreak = event.target.checked; assess(); });
  $('next').addEventListener('click', advance);
  $('reset').addEventListener('click', reset);
  $('export').addEventListener('click', exportResult);
  $('presentation-toggle').addEventListener('click', () => {
    state.presentation = !state.presentation;
    document.body.classList.toggle('presentation', state.presentation);
    $('presentation-toggle').setAttribute('aria-pressed', String(state.presentation));
    $('presentation-toggle').innerHTML = state.presentation ? '✕ 退出投屏' : '<span aria-hidden="true">▣</span> 投屏模式';
    window.scrollTo({ top: 0, behavior: 'instant' });
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.presentation) { $('presentation-toggle').click(); return; }
    if (event.target.closest('input,textarea,select,summary,a') || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); advance(); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); goToPhase(state.phase-1); }
  });
  window.addEventListener('beforeunload', () => activeWorker?.terminate());
  trainModels();
})();
