"""作业2：用Fraction精确计算贝叶斯后验及信息价值。"""
from fractions import Fraction as F
import json
from pathlib import Path

def solve():
    # 状态顺序固定为低信用、中信用、高信用；金额单位为元。
    prior = [F(1,10), F(5,10), F(4,10)]
    payoff = [-200000, 150000, 300000]
    likelihood = {'A': [F(1,10), F(1,10), F(5,10)],
                  'B': [F(4,10), F(5,10), F(4,10)],
                  'C': [F(5,10), F(4,10), F(1,10)]}
    cost, no_sale = 30000, 0
    assert sum(prior) == 1
    for i in range(3):
        assert sum(row[i] for row in likelihood.values()) == 1
    base = sum(p*u for p,u in zip(prior, payoff))
    base_best = max(base, no_sale)
    expected, rows = F(0), []
    for rating, row in likelihood.items():
        joint = [p*l for p,l in zip(prior, row)]
        probability = sum(joint)
        posterior = [p/probability for p in joint]
        emv = sum(p*u for p,u in zip(posterior, payoff))
        expected += probability * max(emv, no_sale)
        rows.append({'rating': rating, 'probability': str(probability),
                     'posterior': [str(p) for p in posterior],
                     'sale_emv_exact': str(emv), 'sale_emv': float(emv),
                     'decision': '赊销' if emv >= no_sale else '拒绝'})
    evpi = sum(p*max(u,no_sale) for p,u in zip(prior,payoff))
    evpi -= base_best
    evsi = expected - base_best
    assert F(0) <= evsi <= evpi
    assert sum(F(r['probability']) for r in rows) == 1
    return {'prior_emv': float(base), 'ratings': rows,
            'sample_value_before_cost': float(expected),
            'EVSI': float(evsi), 'net_after_cost': float(expected-cost),
            'net_gain': float(expected-cost-base_best),
            'EVPI': float(evpi), 'cost': cost}

if __name__ == '__main__':
    result = solve()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path(__file__).with_name('result2.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
