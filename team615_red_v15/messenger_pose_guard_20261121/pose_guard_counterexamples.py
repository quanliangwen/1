"""Exercise the real control/receive/message methods without physics or a match."""
import argparse
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as NS
from unittest.mock import patch

import numpy as np
import pymunk

physics_step_attempts = 0
def forbid_physics(*unused, **kwargs):
    global physics_step_attempts
    physics_step_attempts += 1
    raise AssertionError('Physics stepping is forbidden in this counterexample suite')
pymunk.Space.step = forbid_physics

parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
parser.add_argument('arm', choices=('parent', 'candidate'))
args = parser.parse_args()
saved_argv = sys.argv
sys.argv = ['protocol_counterexamples.py', str(args.archive), 'candidate']
with redirect_stdout(io.StringIO()):
    protocol = runpy.run_path(str(Path(__file__).with_name('protocol_counterexamples.py')))
sys.argv = saved_argv

Flight = protocol['Flight']
RedHooks = protocol['RedHooks']
LBBDRescue = protocol['LBBDRescue']
MessengerRun = protocol['MessengerRun']
NAV = protocol['NAV']
from swarm_rescue.solutions.greedy_mapping import MapMemory
from swarm_rescue.solutions.submission_renderer import SubmissionBearings
from swarm_rescue.solutions.fine_wall_coverage import FineWallCoverage
from swarm_rescue.solutions.final_map_relay import FinalMaps

guarded = args.arm == 'candidate'
outcomes = {}

class CommonWorkComplete(Exception):
    pass

def stop_after_common(*unused):
    raise CommonWorkComplete

def flight(identifier=4, state='ACTIVE', fixed=False, odometry=True, step=2204):
    d = Flight()
    d.identifier, d.elapsed_timestep = identifier, step
    d.grid.pose_fixed, d._odometry_only = fixed, odometry
    d.messenger.state = state
    d.memory = MapMemory(512, 512)
    d.memory.hits[100, 60:120] = 3
    d.memory.free[10, 10] = True
    d.submission_bearings = SubmissionBearings(512, 512)
    d.submission_bearings.bits[50, 30:60] = 1
    d.fine_wall_coverage = FineWallCoverage(d.memory, identifier, 5)
    d.red_packet = (2100, d.memory.packet())
    return d

def evidence(d):
    return (d.memory.hits.tobytes(), d.memory.free.tobytes(), d.memory.visits.tobytes(),
            d.submission_bearings.bits.tobytes(), d.fine_wall_coverage.local_hits.tobytes(),
            d.fine_wall_coverage.sources.tobytes())

def wall_evidence(value):
    return tuple(value[i] for i in (0, 3, 4, 5))

def execute(d, stop=False):
    if stop:
        d._update_drop_hints = stop_after_common
    with patch.object(LBBDRescue, 'control', protocol['base_control']):
        try:
            return RedHooks.control(d)
        except CommonWorkComplete:
            assert stop

# Different invalid localization flags must all protect the old evidence bytes.
invalid = []
for fixed, odometry in ((False, True), (False, False), (True, True)):
    d = flight(fixed=fixed, odometry=odometry)
    before = evidence(d)
    reference = MapMemory(512, 512)
    reference.hits[:] = d.memory.hits
    reference.free[:] = d.memory.free
    reference.visits[:] = d.memory.visits
    reference.observe(d.pose, d.heading, d.lidar_values(), d.lidar_rays_angles(), ())
    command = execute(d)
    after = evidence(d)
    changed = wall_evidence(after) != wall_evidence(before)
    assert changed is not guarded
    if guarded:
        assert wall_evidence(after) == wall_evidence(before)
    else:
        assert after[0] != before[0] and after[3] != before[3]
    assert np.array_equal(d.memory.free, reference.free)
    assert np.array_equal(d.memory.visits, reference.visits)
    assert after[1] != before[1] and after[2] != before[2]
    assert command == NAV and d.base_calls == 1
    invalid.append(dict(pose_fixed=fixed, odometry_only=odometry,
                        local_wall_and_bearing_evidence_changed=changed,
                        free_space_and_visits_match_unguarded_observation=True,
                        navigation_command_unchanged=True))
outcomes['three_unreliable_pose_cases'] = invalid

# GPS/compass reliability restores both wall and incidence observations.
d = flight(fixed=True, odometry=False)
before = evidence(d)
execute(d)
assert evidence(d)[0] != before[0] and evidence(d)[3] != before[3]
assert np.any(d.fine_wall_coverage.local_hits)
outcomes['reliable_active_messenger_still_observes'] = True

d = flight()
before = evidence(d)
execute(d)
if guarded:
    assert wall_evidence(evidence(d)) == wall_evidence(before)
d.grid.pose_fixed, d._odometry_only = True, False
d.elapsed_timestep += 4
d.pose = np.array([16., 8.])
before = evidence(d)
execute(d)
assert evidence(d)[0] != before[0] and evidence(d)[3] != before[3]
outcomes['recovery_resumes_observation_without_resetting_history'] = True

# Scope is exactly drone 4 while ACTIVE. Other existing behavior is untouched.
scope = []
for identifier, state in [(0, 'ACTIVE'), (1, 'ACTIVE'), (2, 'ACTIVE'), (3, 'ACTIVE'),
                          (4, 'IDLE'), (4, 'DONE')]:
    d = flight(identifier=identifier, state=state)
    before = evidence(d)
    execute(d, stop=True)
    assert evidence(d)[0] != before[0] and evidence(d)[3] != before[3]
    scope.append([identifier, state])
outcomes['six_out_of_scope_states_keep_existing_observation'] = scope

for step, missing in ((2205, False), (2204, True)):
    d = flight(fixed=True, odometry=False, step=step)
    if missing:
        d.lidar_values = lambda: None
    before = evidence(d)
    execute(d)
    assert evidence(d) == before
outcomes['existing_four_step_sensor_schedule_and_missing_lidar_behavior'] = True

# A blocked local scan must not block a periodic packet or a contact refresh.
refreshes = []
for step, phase in ((2344, 'APPROACH'), (2204, 'HOLD')):
    d = flight(step=step)
    d.messenger.phase = phase
    before = evidence(d)
    execute(d)
    assert d.red_packet[0] == step and d.cache_calls == 1
    assert d.deadline_submission.backup_step == step
    if guarded:
        assert wall_evidence(evidence(d)) == wall_evidence(before)
    refreshes.append(dict(step=step, phase=phase, packet_version=d.red_packet[0],
                          backup_step=d.deadline_submission.backup_step))
outcomes['periodic_and_contact_refresh_and_backup_continue'] = refreshes

# Use actual RedHooks.receive and define_message_for_all, not a fake merge.
d = flight()
d.search_reconnect = NS(record_contact=lambda *unused: None)
d._receive_team_coordination = lambda *unused: None
d._receive_scan_progress = lambda *unused: None
d._receive_cached_map = lambda *unused: None
d.placement = NS(receive=lambda *unused: None, unlocalized_drops=set(), local_turns=(),
                 branch_exit=NS(receive=lambda *unused: None, claim=None,
                                acknowledgments=lambda *unused: ()),
                 local_exit=NS(receive=lambda *unused: None, packet=lambda *unused: None),
                 deep=NS(passages=NS(receive=lambda *unused: None, reports={})))
d.fast_closeout = NS(receive=lambda *unused: None, packet=lambda *unused: None)
d.team_wall = NS(receive=lambda *unused: None, packet=lambda *unused: None)
d.second_drop = NS(packet=lambda *unused: None)
d.final_reconnect = NS(record=lambda *unused: None)
d.final_maps = FinalMaps(4, 5)
d.drop_records = {}
d.received_maps = {}
d.own_scan_progress = ()
d.drop_hint_revision, d.drop_hints = 0, ()
d._own_map_bid = lambda *unused: None
d._cached_map_offer = lambda *unused: None
d._relay_map_offer = lambda *unused: None
d._advertise_scan_progress = lambda *unused: None
peer = MapMemory(512, 512)
peer.hits[200, 200] = 5
peer.free[25, 25] = True
peer_packet = peer.packet()
peer_bits_id = 100 * d.submission_bearings.bits.shape[1] + 100
incoming = dict(kind='two-stage', id=0, states=(dict(id=0, step=2203),),
                red_map=(2203, peer_packet), red_map_seen={4:2100},
                red_submission_bearings=(2203, np.array([peer_bits_id], np.int32),
                                        np.array([128], np.uint8)),
                red_inventory={i:(2203, 0) for i in (0, 1, 2, 4)})
d.communicator = NS(received_messages=[(None, incoming)])
with patch.object(LBBDRescue, 'receive', lambda *unused: None):
    RedHooks.receive(d)
assert d.memory.hits[200, 200] == 5 and d.memory.free[25, 25]
assert d.submission_bearings.bits.ravel()[peer_bits_id] & 128
assert d.map_revision[0] == 2203 and d.messenger.receipts[0]['map_version'] == 2203
before = evidence(d)
execute(d)
if guarded:
    assert wall_evidence(evidence(d)) == wall_evidence(before)
with patch.object(LBBDRescue, 'define_message_for_all', lambda *unused: dict(id=4)):
    forwarded = RedHooks.define_message_for_all(d)
ids, values, *_ = forwarded['red_map'][1]
assert values[np.flatnonzero(ids == 200 * 256 + 200)[0]] == 5
stamp, ids, values = forwarded['red_submission_bearings']
assert values[np.flatnonzero(ids == peer_bits_id)[0]] & 128
assert forwarded['red_map_seen'][0] == 2203
outcomes['received_wall_and_bearing_evidence_is_merged_and_forwarded'] = True

# Both hard deadlines still preempt navigation and observation on the bad pose.
for step, seconds, reason in ((2204, 178.6, 'walltime'), (5396, 150., 'timestep')):
    d = flight(step=step)
    d.elapsed_walltime = seconds
    before = evidence(d)
    execute(d)
    assert d.base_calls == 0 and evidence(d) == before
    assert np.array_equal(d.sent, d.image)
    assert d.deadline_submission_event['fallback'] == reason
outcomes['unreliable_messenger_both_deadlines_preempt_observation'] = True

assert physics_step_attempts == 0
result = dict(arm=args.arm, status='PASS', physics_steps=0, full_matches=0,
              physics_step_attempts=physics_step_attempts,
              archive_sha256=sha256(args.archive.read_bytes()).hexdigest(),
              red_hooks_loaded_from=sys.modules[RedHooks.__module__].__file__,
              parent_bug_reproduced=not guarded,
              prior_protocol_scenarios=protocol['RESULTS'], scenarios=outcomes)
print(json.dumps(result, indent=2))
