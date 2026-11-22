from hashlib import sha256
from importlib import import_module
import gc
import time
import json
from pathlib import Path
import random
import shutil
import sys
from unittest.mock import patch

stage = Path.cwd()
sealed, source = map(Path, sys.argv[1:3])
map_name = sys.argv[3]
assert map_name == "Map07"
origin = sealed / "official_sdk"
workspace = stage / "official_sdk"
binding_bytes = (sealed / "WORKSPACE_BINDING_FIRST.json").read_bytes()
assert sha256(binding_bytes).hexdigest() == "8a6310cdfccb0bc3c76ee4f4b6d1ab69bd6634f881f3268fb78b6302d8d77585"
binding = json.loads(binding_bytes)
assert binding["official_commit"] == "6557940dc18549ffc7a945db887da5b05b7ed2f1"
assert sha256((sealed / "official_sdk.tar").read_bytes()).hexdigest() == binding["sdk_archive_sha256"]

def sdk_ignore(path, names):
    ignored = {".git", "__pycache__", "results_swarm_rescue"}
    if Path(path) == origin / "src/swarm_rescue":
        ignored.add("solutions")
    return ignored

shutil.copytree(origin, workspace, ignore=sdk_ignore)
for name, expected in binding["sdk_files"].items():
    assert sha256((workspace / name).read_bytes()).hexdigest() == expected, name

def inputs():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(source.iterdir())
            if p.is_file() and p.suffix in {".py", ".yml", ".txt"}}

frozen = inputs()
declared = json.loads((stage/"DECLARED_SOURCE.json").read_bytes())
assert frozen == declared
patch_binding=json.loads((stage/"PATCH_BINDING.json").read_bytes())
assert frozen==patch_binding["candidate"]
assert json.loads((stage/"OFFLINE_CHECK.json").read_bytes())["simulation_steps"]==0
from zipfile import ZipFile
with ZipFile(stage/"baseline_snapshot.zip") as archive:
    baseline = {name:sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
assert baseline == patch_binding["baseline"]
assert sha256((stage/"baseline_snapshot.zip").read_bytes()).hexdigest() == patch_binding["baseline_zip_sha256"]
assert sha256((stage/"candidate_snapshot.zip").read_bytes()).hexdigest() == patch_binding["candidate_zip_sha256"]
(stage/"SOURCE_MATCH.json").write_text(json.dumps(dict(candidate=frozen,
    baseline_commit=patch_binding["baseline_commit"], candidate_zip_sha256=patch_binding["candidate_zip_sha256"],
    changed=patch_binding["changed"]),indent=2)+"\n")
solutions = workspace / "src/swarm_rescue/solutions"
solutions.mkdir()
for name, expected in frozen.items():
    code = (source / name).read_bytes()
    assert sha256(code).hexdigest() == expected, name
    if name.endswith(".py"):
        compile(code, name, "exec")
    (solutions / name).write_bytes(code)
assert inputs() == frozen

def save(name, data):
    (stage / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=lambda v:sorted(v) if isinstance(v,(set,frozenset)) else json_native(v)) + "\n", encoding="utf-8")

sys.path.insert(0, str(workspace / "src"))
import os
os.chdir(workspace)
import numpy as np
import math
from swarm_rescue.launcher import Launcher
MapClass = getattr(import_module(f"swarm_rescue.maps.map_{map_name[-2:]}"), map_name)
from swarm_rescue.solutions.my_drone_eval import drone_class_for_mode
from swarm_rescue.simulation.utils import constants as C
assert drone_class_for_mode("place").__name__ == "RedHooks"
assert (C.MAX_RANGE_LIDAR_SENSOR,C.MAX_RANGE_SEMANTIC_SENSOR,C.RANGE_COMMUNICATION,C.DRONE_INITIAL_HEALTH)==(230,130,180,25)

launch = Launcher(config_path=str(stage / "place_map09.yml"), team_mode="place")
[config] = launch.eval_plan.list_eval_config
assert (config.map_name, config.number_drones, config.initial_bombs_per_drone, config.nb_rounds) == (map_name,5,2,1)
assert {x.name for x in config.zones_config} == {"NO_COM_ZONE","NO_GPS_ZONE"}
seed = 615
random.seed(seed)
np.random.seed(seed)
gc.disable()
sequence = np.random.SeedSequence(seed)
original_rng = np.random.default_rng
original_map_init = MapClass.__init__
rounds = []
arenas = []
scored = []
submissions = []

audit_stream = (stage/"placement_events.jsonl").open("x",encoding="utf8",buffering=1)
timing_stream = (stage/"TIMING_ANCHORS.jsonl").open("x",encoding="utf8",buffering=1)
TIMING_STEPS = {1,501,1001,1501,2001,2501,3001,3240,3501,4001,4340,4501,4590,4751,4950,4991,5021,5022,5030,5051,5251,5501,6001,6501,6695,6696,6710,6725,7001}

def json_native(value):
    if isinstance(value,np.ndarray):
        return value.tolist()
    if isinstance(value,np.generic):
        return value.item()
    raise TypeError(type(value).__name__)

def emit(row):
    audit_stream.write(json.dumps(row, default=json_native, ensure_ascii=False)+"\n")

class Logged(list):
    def __init__(self, drone, source):
        super().__init__()
        self.drone, self.source = drone,source

    def append(self, entry):
        super().append(entry)
        step,event,*values = entry
        if (map_name == "Map08" and self.source == "second_drop" and self.drone.identifier == 4
                and 2090 <= step <= 2225 and event in ("survey", "survey_gate", "opportunity_block")):
            emit(dict(drone=4, step=step, event=event, source=self.source, values=values,
                      backups=self.drone.second_drop.backups))
        if self.source == "drop_departure" and (event.startswith("recovery_") or event == "departure_ended"):
            r=self.drone.drop_departure
            extra={}
            if self.drone.identifier==4 and event.startswith("recovery_"):
                extra=dict(pose=self.drone.pose,first_point=r.first_point,goal=r.recovery_goal,
                    walltime=float(self.drone.elapsed_walltime),prior_scan=r.before_drop_scan,
                    lidar=self.drone.lidar_values(),angles=self.drone.lidar_rays_angles(),
                    semantic=[dict(distance=h.distance,angle=h.angle,kind=getattr(h.entity_type,"name",""),grasped=h.grasped) for h in self.drone.semantic_values() or ()])
            emit(dict(drone=int(self.drone.identifier),step=step,event=event,source=self.source,values=values,**extra))
        if self.source == "messenger":
            emit(dict(drone=int(self.drone.identifier), step=step, event=event,
                      source=self.source, values=values))
        if event in ("reserve","greedy_first_reserve","reservation_cancelled","greedy_first_cancelled",
                     "candidate_review","reserve_review","reserve_gate","exit_probe","expired","target_blocked",
                     "sensor_unavailable","arrival_rejected","arrived","live_corridor_rejected","sdk_fallback",
                     "on_route_request","site_drop_request","site_drop_result","narrow_request","narrow_block","isolated_window_complete","request","confirmed","rejected","departure_started","departure_path",
                     "departure_clear","departure_odom_lost","departure_replan","escape_reached",
                     "completion_started","completion_review","completion_rejected","completion_expired",
                     "wall_task_reserve","wall_task_end","wall_task_release","wall_task_no_route"):
            emit(dict(drone=int(self.drone.identifier),step=step,event=event,
                      source=self.source,values=values))

stock_states = {}
recovery_states = {}

def observed_control(drone, method):
    def execute():
        prior_packet = None if drone.red_packet is None else drone.red_packet[0]
        prior = drone.pending_drop
        step = int(drone.elapsed_timestep)
        if drone.identifier == 0 and step in TIMING_STEPS:
            timing_stream.write(json.dumps(dict(step=step, walltime=float(drone.elapsed_walltime),
                host_monotonic=time.monotonic(), host_unix=time.time()))+"\n")
        prior_wall = drone.team_wall.reservation
        result = method()
        if step >= drone.limit*2//5:
            counts = tuple(drone.inventory_records.get(owner,(-1,None))[1] for owner in range(drone.team_size))
            if counts != stock_states.get(drone.identifier):
                stock_states[drone.identifier] = counts
                emit(dict(drone=int(drone.identifier),step=step,event="ordinary_inventory_gate",
                          team_confirmed=drone._all_inventory_empty(),records=dict(drone.inventory_records),
                          local_inventory=int(drone.carried_bombs_count()),pending=drone.pending_drop is not None))
        if prior is not None and step>prior[2]:
            stock,pose,request_step = prior
            remaining = int(drone.carried_bombs_count())
            emit(dict(drone=int(drone.identifier),step=step,event="inventory_result",
                      request_step=request_step,before=stock,remaining=remaining,confirmed=remaining<stock))
        if prior_wall is not None and drone.team_wall.reservation is None:
            emit(dict(drone=int(drone.identifier),step=step,event="legacy_reservation_ended",
                      reservation_step=prior_wall[0],point=prior_wall[1],
                      stock_changed=prior_wall[2]!=drone.previous_inventory))
        packet_stamp = None if drone.red_packet is None else drone.red_packet[0]
        if drone.identifier == 4 and step >= 2160 and packet_stamp != prior_packet:
            emit(dict(drone=4, step=step, event="messenger_map_refresh", version=packet_stamp,
                      state=drone.messenger.state, phase=drone.messenger.phase,
                      source_versions=dict(drone.map_revision)))
        if result.get("place_bomb"):
            pending = drone.pending_drop
            request = drone.placement.request
            seconds = float(drone.elapsed_walltime)
            odom = drone.odometer_values()
            emit(dict(drone=int(drone.identifier),step=step,event="request",
                inventory=None if pending is None else pending[0],
                branch=None if request is None else request[1],
                pose=drone.pose if pending is None else pending[1],
                plan=None, reserved=(drone.second_drop.plan[1] if drone.second_drop.plan else
                     drone.team_wall.reservation[1] if drone.team_wall.reservation else None),
                gps_fixed=bool(drone.grid.pose_fixed),speed=None if odom is None else float(odom[0]),
                walltime_seconds=seconds))
        if drone.identifier==4:
            r=drone.drop_departure
            state=(r.recovery_failed,r.recovery_used,r.started,r.recovery_started,
                   r.before_drop_scan is not None,r.first_point is not None,len(r.recovery_trace)==30)
            if state!=recovery_states.get(4) or step in (1356,1418,1450,1500,1620,2700,3240,4000,5022):
                recovery_states[4]=state
                emit(dict(drone=4,step=step,event="recovery_state_observed",state=state,
                    pose=drone.pose,first_point=r.first_point,
                    distance=None if r.first_point is None else float(np.linalg.norm(drone.pose-r.first_point)),
                    trace_span=None if not r.recovery_trace else step-r.recovery_trace[0][0],
                    trace_movement=None if not r.recovery_trace else float(max(np.linalg.norm(p-r.recovery_trace[0][1]) for _,p in r.recovery_trace)),
                    prior_scan_step=None if r.before_drop_scan is None else r.before_drop_scan[0],
                    fixed=bool(drone.grid.pose_fixed and not drone._odometry_only),
                    inventory=int(drone.carried_bombs_count()),pending=drone.pending_drop is not None,
                    walltime=float(drone.elapsed_walltime)))
        return result
    return execute


def map_init(self, *args, **kwargs):
    def seeded_rng(wanted=None):
        return original_rng(sequence.spawn(1)[0] if wanted is None else wanted)
    with patch.object(np.random, "default_rng", seeded_rng):
        original_map_init(self, *args, **kwargs)
    spawn = [[list(point),heading] for point,heading in self._drones_pos]
    evidence = json.loads((stage / "matched_spawns.json").read_bytes())
    assert spawn == evidence[map_name], spawn
    zones = {name:sum(type(e).__name__==name for e in self.playground.elements)
             for name in ("NoGpsZone","NoComZone")}
    assert zones == json.loads((stage / "EXPECTED_ZONES.json").read_bytes())[map_name]
    assert (self.max_timestep_limit,self.max_walltime_limit,self.number_drones) == (7200,240,5) if map_name=='Map05' else (self.max_timestep_limit,self.max_walltime_limit,self.number_drones) == (5400,180,5)
    for drone in self.drones:
        for name in ("team_wall","second_drop","placement","drop_departure","local_escape","fast_closeout","messenger"):
            getattr(drone,name).audit = Logged(drone,name)
        drone.control = observed_control(drone,drone.control)
    arenas.append(self)
    rounds.append(dict(spawn=spawn,zones=zones))
    assert len(rounds)==1
    save("START.json",dict(seed=seed,sdk=binding["official_commit"],sdk_archive_sha256=binding["sdk_archive_sha256"],
         solutions_sha256=frozen,drones=5,bombs_per_drone=2,timestep_limit=self.max_timestep_limit,walltime_limit=self.max_walltime_limit,
         competition_mode=True,map_name=map_name,**rounds[0]))

from swarm_rescue.simulation.reporting.place_score_manager import PlaceScoreManager
from swarm_rescue.simulation.drone.bomb_deployer import BombDeployer
Drone = drone_class_for_mode("place")
original_submit = Drone.submit_exploration_map
original_score = PlaceScoreManager.compute_phase1_score
original_physical_place = BombDeployer._try_place_bomb

def record_physical_place(deployer):
    placed = original_physical_place(deployer)
    agent = deployer._anchor.agent
    point = deployer._placement_map._bombs[-1].true_position() if placed else None
    emit(dict(drone=int(agent.identifier),step=int(agent.elapsed_timestep),event="sdk_placement",
              accepted=bool(placed),physical_xy=None if point is None else tuple(float(v) for v in point)))
    return placed

def observe_submission(drone,image):
    result = original_submit(drone,image)
    submissions.append(dict(drone=int(drone.identifier),step=int(drone.elapsed_timestep),
        walltime_seconds=float(drone.elapsed_walltime),
        image_sha256=sha256(drone._exploration_map_submission.tobytes()).hexdigest()))
    return result

def observe_score(manager, truth, submitted, **kw):
    if map_name in ("Map05", "Map06", "Map07"):
        np.savez_compressed(stage/"wall_geometry.npz", walls=kw["wall_grid"], boundary=kw["boundary_grid"])
    result = original_score(manager,truth,submitted,**kw)
    scored.append(dict(map_score=result.score_map,coverage=result.score_wall,time_score=result.score_time,
        partial=result.round_score,elapsed_walltime=float(kw["elapsed_walltime"]),
        walltime_limit=kw["max_walltime_limit"],steps=kw["elapsed_timestep"],
        placed=kw["placed_count"],expected=kw["expected_count"],
        trajectory=kw["score_exploration_trajectory"],wall_breakdown=result.wall_breakdown,
        submitted_map=submitted is not None,map_breakdown=result.map_breakdown,
        selected_image_sha256=None if submitted is None else sha256(np.asarray(submitted).tobytes()).hexdigest()))
    return result

from swarm_rescue.simulation.gui_map import gui_sr

original_run_control = gui_sr.run_control

def observe_checked_control(drone):
    result = original_run_control(drone)
    step = int(drone.elapsed_timestep)
    if map_name == "Map08" and 2178 <= step <= 2320 and drone.identifier in (0, 2, 3, 4):
        messages = [msg for _, msg in drone.communicator.received_messages
                    if isinstance(msg, dict) and msg.get("kind") == "two-stage" and msg.get("id") == 4]
        direct = [(msg.get("red_inventory", {}).get(4), msg.get("red_wall_reservation")) for msg in messages]
        semantic = [(hit.entity_type.name, float(hit.distance), float(hit.angle))
                    for hit in (drone.semantic_values() or ()) if hit.entity_type.name in ("DRONE", "BOMB")]
        route = None if not drone.route else drone.route[0]
        task = None if drone.search_task is None else drone.search_task.started
        emit(dict(drone=int(drone.identifier), step=step, event="trace", command=result,
            pose=drone.pose, pose_fixed=bool(drone.grid.pose_fixed), heading=drone.heading,
            physical_xy=drone.true_position(), health=drone.drone_health, route=route,
            task=task, mode=drone.mode, inventory=drone.previous_inventory,
            site_plan=drone.second_drop.plan, deep_zone=drone.placement.deep.zone, wall_reservation=drone.team_wall.reservation,
            closeout_plan=drone.fast_closeout.plan, closeout_target=drone.fast_closeout.target,
            closeout_phase=drone.fast_closeout.phase(step),
            peer4_inventory=drone.inventory_records.get(4), peer4_reservation=drone.team_wall.peer.get(4),
            peer4_drop=drone.drop_records.get((4,2)), direct_from4=direct, semantic=semantic))
    return result

assert not (stage/"START.json").exists()
with patch.object(MapClass,"__init__",map_init), patch.object(Drone,"submit_exploration_map",observe_submission), \
     patch.object(PlaceScoreManager,"compute_phase1_score",observe_score), \
     patch.object(BombDeployer,"_try_place_bomb",record_physical_place), \
     patch.object(gui_sr,"run_control",observe_checked_control):
    success=launch.go(headless=True, competition_mode=True, stop_at_first_crash=True)
assert success and len(rounds)==len(scored)==1
score = scored[0]
audit_stream.close()
timing_stream.close()
matching = [found for found in submissions if found["image_sha256"] == score["selected_image_sha256"]]
selected = min(matching,key=lambda row:row["drone"]) if matching else None
if score["submitted_map"] and selected is None:
    selected = dict(step=score["steps"],drone=None,identification="SDK round end, submission hook unmatched")
[arena] = arenas
details = [dict(drone=int(d.identifier),health=int(d.drone_health),inventory=int(d.carried_bombs_count()),
             last_confirmation=d.last_confirmed_drop_step,walltime_submission=d.deadline_submission_event,
             budget_submission=getattr(d,'budget_submission_event',None),budget_submission_audit=getattr(d,'budget_submission_audit',[]),
             group_early_finish_started=d.group_exchange.early_finish_started,
             group_confirmation_retry_used=d.group_exchange.confirmation_retry_used,
             group_peer_zero_receipts=d.group_exchange.peer_zero_receipts,
             drop_departure_audit=d.drop_departure.audit,
             first_drop_recovery=dict(failed=d.drop_departure.recovery_failed,used=d.drop_departure.recovery_used,
                 started=d.drop_departure.recovery_started,first_point=d.drop_departure.first_point,
                 prior_scan=d.drop_departure.before_drop_scan),
             second_drop_audit=d.second_drop.audit,
             messenger_audit=d.messenger.audit,
             team_exchange_audit=d.team_exchange_audit,
             final_inventory_records=d.inventory_records,
             final_source_versions=dict(d.map_revision),
             group_ordinary_selection=d.group_exchange.ordinary_selection,
             group_finish_refresh_step=d.group_exchange.finish_refresh_step,
             group_end_slot=d.group_exchange.submission_slot(d,int(d.elapsed_timestep)),
             original_first_ready=d.first_ready_to_submit_step,
             original_map_quality=d.map_quality,
             original_map_bids=d.map_bids,
             original_same_step_bid_comparisons=d.last_eligible_bid_comparison,
             original_own_sent_bids=list(d.own_sent_bids),
             original_priority_audit=d.submission_priority_audit,
             original_wait_started=d.submission_wait_started,
             original_wait_for=d.submission_wait_for,
             group_final_snapshot_count=len(d.final_maps.snapshots),
             group_final_snapshot_origins=sorted(d.final_maps.snapshots),
             group_first_round_window=(d.group_exchange.finish_floor(d),d.group_exchange.finish_floor(d)+d.team_size*d.group_exchange.SUBMISSION_SLOT_STEPS),
             group_yielding_at_end=d.group_exchange.yield_first_round(d,int(d.elapsed_timestep)),
             group_phase=d.group_exchange.phase,
             group_started=d.group_exchange.started_step,
             group_root=d.group_exchange.plan.root,
             group_root_acks=sorted(d.group_exchange.plan.acks),
             group_branch=d.group_exchange.plan.branch_group,
             group_local_region=d.group_exchange.plan.local_region,
             group_audit=d.group_exchange.audit,
             group_plan_audit=d.group_exchange.plan.audit,
             group_candidate_audit=d.group_exchange.candidates.audit,
             group_manifest=d.group_exchange.candidates.manifest(),
             group_choice=d.group_exchange.choice,
             group_score_table=d.group_exchange.candidates.score_table,
             group_reference_digest=d.group_exchange.candidates.reference_digest,
             group_final_trail=d.group_exchange.plan.trail,
             group_live_version=d.group_exchange.candidates.live_version,
             group_best_metadata=d.group_exchange.candidates.best,
             group_last_comparison_step=d.group_exchange.last_comparison_step,
             group_submission_ready=d.group_exchange.submission_ready,
             group_cached_image_sha256=(None if d.group_best_image is None else
                 sha256(d.group_best_image[0].tobytes()).hexdigest()),
             final_estimated_pose=None if d.pose is None else tuple(map(float,d.pose)),

             closeout_departure_audit=d.closeout.audit,
             fast_closeout_audit=d.fast_closeout.audit,
             freeze_audit=d.pre_submit_scan.audit,
             late_footprints=[row for row in d.fast_closeout.audit if row[1]=="last_bomb_route_target"],
             last_bomb_passes=[row for row in d.placement.audit if row[1]=="last_bomb_gain"],
             placement_rejections=d.placement.blocks) for d in arena.drones]
save("OFFICIAL_SCORE.json",dict(**score,submissions=submissions,selected_submission=selected,drone_details=details,
    placement_events_sha256=sha256((stage/"placement_events.jsonl").read_bytes()).hexdigest(),
    wall_geometry_sha256=sha256((stage/"wall_geometry.npz").read_bytes()).hexdigest() if map_name in ("Map05", "Map06", "Map07") else None))
[result] = (workspace/"results_swarm_rescue").glob("team*")
files={p.relative_to(result).as_posix():sha256(p.read_bytes()).hexdigest() for p in result.rglob("*") if p.is_file()}
assert sum(n.endswith(".npz") for n in files)==1
save("FINISH.json",dict(status="COMPLETE",completed_red_rounds=1,blue_rounds=0,layout_evaluations=0,
                         result_dir=str(result),files=files))
print(result, flush=True)




# Read-only exports after official scoring. No controller/physics replay.
arrays={}
metadata={}
for d in arena.drones:
    owner=int(d.identifier);c=d.group_exchange.candidates
    metadata[owner]=dict(width=c.width,height=c.height,images={},snapshots={},live_version=c.live_version)
    if c.live_image is not None:arrays[f'd{owner}_latest_live']=np.packbits(c.live_image.astype(bool).ravel())
    for slot,data in c.images.items():
        key=f"d{owner}_image{slot}"
        arrays[key]=data['packed']
        metadata[owner]['images'][slot]=dict(version=data['version'],digest=data['digest'],sources=data['sources'])
    for snapshot_owner,data in c.snapshots.items():
        prefix=f"d{owner}_snapshot{snapshot_owner}"
        for suffix,value in zip(('indices','values','free','visits'),data['memory']):arrays[prefix+'_'+suffix]=value
        arrays[prefix+'_bearings']=data['bearings']
        metadata[owner]['snapshots'][snapshot_owner]=dict(version=data['version'],digest=data['digest'],inventory=data['inventory'])
    for suffix,value in zip(('indices','values','free','visits'),d.memory.packet()):arrays[f"d{owner}_final_"+suffix]=value
    arrays[f"d{owner}_final_bearings"]=d.submission_bearings.bits
    if d.group_best_image is not None:arrays[f"d{owner}_selected_cache"]=np.packbits(d.group_best_image[0].astype(bool).ravel())
np.savez_compressed(stage/'group_dataset.npz',**arrays)
save('GROUP_DATASET.json',metadata)
assert inputs()==frozen
runtime={p.name:sha256(p.read_bytes()).hexdigest() for p in solutions.iterdir() if p.is_file() and p.suffix in {'.py','.yml','.txt'}}
assert runtime==frozen
save('POST_RUN_SOURCE_CHECK.json',dict(status='PASS',source_members=len(frozen),input_unchanged=True,runtime_unchanged=True))
save('EXTRA_ARTIFACTS.json',{name:sha256((stage/name).read_bytes()).hexdigest() for name in
    ('group_dataset.npz','GROUP_DATASET.json','POST_RUN_SOURCE_CHECK.json')})
