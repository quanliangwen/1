from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
import json
import math
import random
import sys
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np

root = Path(__file__).resolve().parent
sealed = Path(sys.argv[1])
binding_data = (sealed / "WORKSPACE_BINDING_FIRST.json").read_bytes()
assert sha256(binding_data).hexdigest() == "8a6310cdfccb0bc3c76ee4f4b6d1ab69bd6634f881f3268fb78b6302d8d77585"
binding = json.loads(binding_data)
sdk = sealed / "official_sdk"
for name, expected in binding["sdk_files"].items():
    assert sha256((sdk / name).read_bytes()).hexdigest() == expected, name
payload = root / "candidate.zip"
payload_hash = sha256(payload.read_bytes()).hexdigest()
assert payload_hash == "0cad0c65622e54740a0e6c2e7d61359fcf2e826efc8293808cedb150fa7770ff"
solution = root / "solution"
with ZipFile(payload) as archive:
    assert all(Path(name).name == name for name in archive.namelist())
    archive.extractall(solution)

sys.path.insert(0, str(sdk / "src"))
from swarm_rescue import solutions
solutions.__path__.insert(0, str(solution))
from swarm_rescue.maps.map_08 import Map08
from swarm_rescue.simulation.drone.bomb_deployer import BombDeployer
from swarm_rescue.simulation.elements.sensor_disablers import ZoneType
from swarm_rescue.solutions.my_drone_eval import drone_class_for_mode
from swarm_rescue.solutions.placement_maneuvers import speed_and_velocity

Pilot = drone_class_for_mode("place")
assert Path(sys.modules[Pilot.__module__].__file__).parent == solution

FACE_Y = 296.
EXIT_X = -55.
START_Y = FACE_Y - 56.
START_STEP = 1700
NOMINAL_GAIN, GAIN_FLOOR = 1.2, .8

def angle_delta(target, actual):
    return (target - actual + math.pi) % math.tau - math.pi

def floats(v):
    return list(map(float, v))

def observed(drone, *, exiting=False):
    g = drone.measured_gps_position()
    h = drone.measured_compass_angle()
    scan = drone.lidar_values()
    assert g is not None and h is not None and scan is not None
    drone.heading = float(h)
    relative = np.asarray(drone.lidar_rays_angles()) + h - math.pi / 2.
    profile = np.asarray(scan) * np.cos(relative)
    usable = (np.cos(relative) >= math.cos(.26)) & np.isfinite(profile) & (profile > 0.)
    if exiting:
        # A just-created bomb surrounds the lidar ray origin. Follow the
        # exit checked before release using GPS for transverse feedback.
        gap = float(FACE_Y - g[1])
    else:
        assert usable.sum() >= 5
        gap = float(np.median(profile[usable]))
    drone.pose = np.array([g[0], FACE_Y - gap])
    velocity = speed_and_velocity(drone)
    assert velocity is not None
    return gap, velocity, scan, drone.semantic_values() or ()

def helm(drone, desired, velocity, target_heading):
    heading_error = angle_delta(target_heading, drone.heading)
    # Identical world-frame velocity feedback, with yaw held separately.
    command = drone.motion_command(np.asarray(desired), velocity,
                                   heading_error * 3., .65, False)
    return dict(command, place_bomb=0)

def prepare(seed, heading):
    random.seed(seed)
    np.random.seed(seed)
    seq, original_rng = np.random.SeedSequence(seed), np.random.default_rng
    def seeded(wanted=None):
        return original_rng(seq.spawn(1)[0] if wanted is None else wanted)
    with patch.object(np.random, "default_rng", seeded):
        arena = Map08(Pilot, (ZoneType.NO_COM_ZONE, ZoneType.NO_GPS_ZONE), 1)
    [d] = arena.drones
    d.enable_bomb_deployer(arena, initial_count=1)
    d.initial_inventory, d.previous_inventory = 2, 1
    d.base.move_to(((0., START_Y), heading))
    d.elapsed_timestep, d.elapsed_walltime = START_STEP, 45.
    d.grid.pose_fixed, d._odometry_only = True, False
    d.search_roaming.departed = True
    d.grid.evidence.fill(-8)
    wall_row, _ = d.grid.cell((0., FACE_Y))
    d.grid.evidence[wall_row, :] = 8
    d.grid.refresh()
    return arena, d

def trial(seed, target_gap, arm):
    heading = math.pi if arm == "side" else math.pi / 2.
    print("case", seed, target_gap, arm, file=sys.stderr, flush=True)
    arena, d = prepare(seed, heading)
    ticks = 0
    minimum_gap = math.inf
    health = int(d.drone_health)
    events = []
    gates = []
    origin = BombDeployer._try_place_bomb
    confirmed = None

    def step(command):
        nonlocal ticks, minimum_gap
        arena.playground.step({d: command})
        ticks += 1
        d.elapsed_timestep = START_STEP + ticks
        d.elapsed_walltime = 45. + ticks / 30.
        minimum_gap = min(minimum_gap, FACE_Y - float(d.true_position()[1]))

    def observe_pulse(deployer):
        agent = deployer._anchor.agent
        before = deployer.inventory
        ok = origin(deployer)
        bomb = arena._bombs[-1] if ok else None
        events.append(dict(accepted=bool(ok), center=floats(agent.true_position()),
            angle=float(agent.true_angle()), speed=float(np.linalg.norm(agent.true_velocity())),
            bomb=None if bomb is None else floats(bomb.true_position()), before=before, after=deployer.inventory))
        return ok

    step(dict(forward=0., lateral=0., rotation=0., grasper=0, place_bomb=0))
    stable = 0
    for _ in range(115):
        gap, motion, scan, semantic = observed(d)
        desired = (0., float(np.clip((gap - target_gap) / 7., -.55, 1.25)))
        command = helm(d, desired, motion[1], heading)
        ready = abs(gap - target_gap) <= 1.5 and abs(motion[0]) <= .65
        stable = stable + 1 if ready else 0
        if stable >= 2:
            d.route = [tuple(d.pose + np.array([-85., 0.]))]
            blocks = d.second_drop.current_blocks(d, d.elapsed_timestep, scan, semantic, NOMINAL_GAIN, GAIN_FLOOR)
            gates.append(dict(tick=ticks, lidar_gap=gap,
                              true_gap=FACE_Y-float(d.true_position()[1]), blocks=blocks))
            if not blocks:
                assert d.second_drop.request(d, command, d.elapsed_timestep, "on_route_second")
                with patch.object(BombDeployer, "_try_place_bomb", observe_pulse):
                    step(command)
                d._sync_placement(d.elapsed_timestep)
                d.placement.finish_request(d, d.elapsed_timestep)
                confirmed = d.carried_bombs_count() == 0
                assert bool(events) and events[0]["accepted"] == confirmed
                break
        step(command)

    release_tick = ticks if confirmed else None
    before_exit = d.true_position().copy()
    exit_begin = ticks
    aligned = exit_reached = aligned_and_reached = None
    flight_after = []
    release_exit_lidar_maxima = []
    for _ in range(85):
        gap, motion, scan, semantic = observed(d, exiting=True)
        if len(release_exit_lidar_maxima) < 12:
            release_exit_lidar_maxima.append(float(np.nanmax(scan)))
        desired = (-1.8, float(np.clip((gap - target_gap) / 7., -.55, .55)))
        # Both use lateral flight as needed and pursue the same exit pose.
        step(helm(d, desired, motion[1], math.pi))
        elapsed = ticks - exit_begin
        reached = float(d.true_position()[0]) - float(before_exit[0]) <= EXIT_X
        aligned_now = abs(angle_delta(math.pi, d.true_angle())) <= math.radians(8.)
        if aligned_now and aligned is None:
            aligned = elapsed
        if reached and exit_reached is None:
            exit_reached = elapsed
        if reached and aligned_now and aligned_and_reached is None:
            aligned_and_reached = elapsed
        if confirmed:
            flight_after.append(floats(arena._bombs[-1].true_position()))
        if aligned_and_reached is not None and elapsed >= 25:
            break
    event = events[0] if events else None
    drift = max((math.dist(event["bomb"], point) for point in flight_after), default=None) if confirmed else None
    assert not confirmed or (event["center"] == event["bomb"] and drift < .01)
    return dict(seed=seed, target_gap=target_gap, arm=arm, physics_steps=ticks,
                sdk_event=event, inventory_confirmed=bool(confirmed), release_tick=release_tick,
                actual_bomb_gap=None if not confirmed else FACE_Y - event["bomb"][1],
                true_minimum_gap=minimum_gap, health_loss=health-int(d.drone_health), gates=gates,
                aligned_exit_tick=aligned, reached_exit_tick=exit_reached,
                reached_and_aligned_tick=aligned_and_reached, maximum_bomb_drift=drift,
                exit_first_lidar_maxima=release_exit_lidar_maxima)

seeds = (615, 616, 617)
distances = (24., 30., 38.)
with redirect_stdout(StringIO()):
    trials = [trial(s, g, arm) for g in distances for s in seeds for arm in ("front", "side")]

assert len(trials) == 18
data = dict(sdk=binding["official_commit"], source_sha256=payload_hash, map="Map08",
            full_rounds=0, physics_steps=sum(row["physics_steps"] for row in trials),
            test_design={"seeds":seeds, "start_gap":56., "release_distances":distances,
                         "exit_travel_px":-EXIT_X, "wall_face_y":FACE_Y,
                         "fixture":"one drone; common start position and preassigned approach bearing; original sensor noise; seeded local free/blocked cells, route, first-bomb depletion, and positive coverage gain; actual release gates, SDK actuator, and inventory readback; exit uses GPS/odometry along the prechecked path, since the newly created bomb can obscure the lidar at the ray origin; no run of squad scheduler"},
            trials=trials)
print(json.dumps(data, indent=2))


