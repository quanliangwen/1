"""Read audited own RED logs and public finalized scores; no SDK/native execution."""
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREV = Path('E:/codex/P48_astar_five_20261102')
REMOTE = '/home/junhao/quan/parallel_test_solver/match/results/target90_20261012/unseeded_sdk_e2f022b_P48_ASTAR_FIVE_20261102_FIRST'

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def save(name, obj):
    path = HERE / name
    assert not path.exists(), path
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def main():
    assert not (HERE / 'BASELINE_DIAGNOSIS_FIRST.json').exists()
    campaign = load(PREV / 'CAMPAIGN_CLIENT_REVIEW.json')
    assert campaign['status'] == 'PASS' and not campaign['native_failure']
    raw = load(PREV / 'P48_ASTAR_A/RAW_SHA256.json')
    records = []
    for scored in campaign['result']['rows']:
        name = scored['map']
        rel = f'{name}_red/console.log'
        # The already audited manifest binds this own diagnostic input. This is
        # not a second archive download/audit, and no BLUE log is read.
        run = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                              'junhao@10.112.162.60', 'cat', f'{REMOTE}/{rel}'],
                             capture_output=True, check=True, timeout=45)
        assert hashlib.sha256(run.stdout).hexdigest() == raw[rel]['sha256']
        lines = run.stdout.decode('utf-8', errors='strict').splitlines()
        fresh, drops, releases, farthest, prefix = [], [], [], [], []
        labels = Counter()
        for line in lines:
            if line.startswith('['):
                labels[line.split(']', 1)[0] + ']'] += 1
            if line.startswith('[FRESH_OPPORTUNITY] '):
                fresh.append(json.loads(line.split('] ', 1)[1]))
            elif line.startswith('[placement]'):
                m = re.search(r'drone=(\d+) step=(\d+) inventory=(\d+) position=\(([-\d.]+),([-\d.]+)\)', line)
                assert m, line
                own, step, inv, x, y = m.groups()
                drops.append(dict(owner=int(own), step=int(step), inventory=int(inv), position=[float(x), float(y)]))
            elif line.startswith('[active-coverage] release_all_inventory '):
                match = re.match(r'\[active-coverage\] release_all_inventory (\d+) (\d+) (.*)', line)
                assert match, line
                own, step, payload = match.groups()
                releases.append(dict(owner=int(own), step=int(step), model=ast.literal_eval(payload)))
            elif line.startswith('[farthest-wall] '):
                farthest.append(ast.literal_eval(line.split('] ', 1)[1]))
            elif line.startswith('[reserved-prefix-budget] '):
                match = re.match(r'\[reserved-prefix-budget\] (\d+) (\d+) (.*)', line)
                assert match, line
                prefix.append(dict(owner=int(match[1]), step=int(match[2]), context=ast.literal_eval(match[3])))
        phase = scored['phase']
        b = phase['map_breakdown']
        submitted = [e for e in fresh if e['kind'] == 'SUBMIT_IMAGE']
        due = [e for e in fresh if e['kind'] == 'ACTUAL_SUBMISSION_DUE']
        assert drops and submitted
        reported_calls = sum(e.get('astar_stats', {}).get('calls', 0) for e in submitted)
        reported_search_sec = sum(e.get('astar_stats', {}).get('seconds', 0) for e in submitted)
        records.append(dict(
            map=name, full=scored['full'], score_map=phase['score_map'], score_wall=phase['score_wall'], score_time=phase['score_time'],
            own_console_binding=raw[rel], label_counts=dict(labels),
            map_credit_percent=100*b['credit'], map_penalty_percentage_points=100*b['penalty'],
            missed_surface_total_point_gap=50*(1-b['credit']), false_positive_total_point_gap=50*b['penalty'],
            wall_total_point_gap=.2*(100-phase['score_wall']), time_total_point_gap=.1*(100-phase['score_time']),
            releases=releases, placements=drops, submission_due=due, submissions=submitted,
            first_release=min((e['step'] for e in releases), default=None), first_drop=min(e['step'] for e in drops),
            last_drop=max(e['step'] for e in drops), submission_step=min(e['step'] for e in submitted),
            tail_after_last_drop=min(e['step'] for e in submitted)-max(e['step'] for e in drops),
            farthest=dict(calls=len(farthest), reasons=dict(Counter(e.get('reason','unknown') for e in farthest)),
                          accepted=sum(bool(e.get('selected_changed')) for e in farthest),
                          enclosing_seconds_sum=sum(e.get('enclosing_elapsed_seconds',0) for e in farthest),
                          note='Enclosing intervals may contain other work. This is not exclusive CPU attribution.', events=farthest),
            prefix_events=prefix, reported_astar_calls=reported_calls, reported_astar_search_seconds=reported_search_sec,
            astar_scope_note='Only submitting owners report counters; other owners are not observed. Search excludes full distance fields/masks/smoothing/control.'
        ))
    result = dict(status='PASS_EXISTING_AUDITED_OWN_LOG_DIAGNOSIS', sdk_frames=0, native_runs=0,
                  source_campaign_sha256=hashlib.sha256((PREV/'CAMPAIGN_CLIENT_REVIEW.json').read_bytes()).hexdigest(),
                  rows=records, production_inputs_changed=False, archive_reaudited=False,
                  limits=['No target/version chain in current logs: cannot attribute low coverage to failed task execution.',
                          'Map scoring credit and penalty are finalized public aggregates, not policy inputs.',
                          'Natural episodes are not paired causal comparisons.'])
    save('BASELINE_DIAGNOSIS_FIRST.json', result)
    print(json.dumps([dict(map=r['map'], credit=r['map_credit_percent'], penalty=r['map_penalty_percentage_points'],
                           first_release=r['first_release'], first_drop=r['first_drop'], last_drop=r['last_drop'],
                           tail=r['tail_after_last_drop'], farthest_calls=r['farthest']['calls'],
                           farthest_accepted=r['farthest']['accepted'], farthest_reasons=r['farthest']['reasons'],
                           reported_search_seconds=r['reported_astar_search_seconds']) for r in records], ensure_ascii=False))

if __name__ == '__main__':
    main()
