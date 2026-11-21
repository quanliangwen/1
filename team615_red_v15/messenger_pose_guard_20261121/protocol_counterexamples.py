"""Run protocol counterexamples through ZIP modules and the real control entry."""
import argparse
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import json

import numpy as np
import swarm_rescue.solutions

parser=argparse.ArgumentParser()
parser.add_argument("archive",type=Path)
parser.add_argument("arm",choices=("baseline","candidate"))
args=parser.parse_args()
candidate=args.arm=="candidate"
swarm_rescue.solutions.__path__=[str(args.archive.resolve())]

from swarm_rescue.solutions.messenger_run import MessengerRun, IDLE, ACTIVE, DONE, APPROACH, HOLD
from swarm_rescue.solutions.red_hooks import RedHooks
from swarm_rescue.solutions.lbbd_rescue import LBBDRescue
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan

NAV=dict(forward=.2,lateral=.1,rotation=0.,grasper=0,place_bomb=0)
RESULTS={}

def noop(*args,**kwargs):
    pass

def drive(*args,**kwargs):
    return NAV.copy()

def drone():
    return NS(identifier=4,team_size=5,limit=5400,walltime_limit=180.,elapsed_walltime=75.,
              previous_inventory=0,pending_drop=None,pose=np.zeros(2),heading=0.,
              states={i:dict(point=(500.+i*30.,0.),health=25) for i in range(4)},
              inventory_records={i:(2100,int(i==3)) for i in range(5)},
              map_revision={i:2100 for i in range(4)},red_packet=(2100,()),
              communicator_is_disabled=lambda:False,drive=drive,measured_velocity=lambda:np.zeros(2))

def message(d,sender,step,seen=None,empty=None,map_version=None,state_stamp=None):
    stamp=step if state_stamp is None else state_stamp
    version=step if map_version is None else map_version
    d.map_revision[sender]=max(d.map_revision.get(sender,-1),version)
    return dict(id=sender,states=(dict(id=sender,step=stamp),),red_map=(version,()),
                red_map_seen={} if seen is None else {4:seen},
                red_inventory={i:(min(stamp,2100),0) for i in (empty or ())})

def tick(m,d,step):
    command=NAV.copy()
    m.tick(d,step,command,d.limit-step)
    return command

def activate(m,d):
    tick(m,d,2160)
    assert m.state==ACTIVE

# An estimated nearby point alone used to count as a contact.
m,d=MessengerRun(),drone()
d.states[0]["point"]=(10.,0.)
activate(m,d)
tick(m,d,2161)
if not candidate:
    assert m.phase==HOLD
    for step in range(2162,2174):
        tick(m,d,step)
    assert any(row[1]=="exchange_complete" for row in m.audit)
    RESULTS["nearby_without_receipt"]="baseline falsely reports exchange complete"
else:
    assert m.phase==APPROACH and not any(row[1]=="contact" for row in m.audit)
    RESULTS["nearby_without_receipt"]=True

if candidate:
    # Stale and relayed peer state cannot establish a live direct contact.
    m.receive(d,message(d,0,2161,state_stamp=2100,map_version=2100),2161)
    assert 0 not in m.receipts
    msg=message(d,0,2162)
    msg["states"]=(dict(id=1,step=2162),)
    m.receive(d,msg,2162)
    assert 0 not in m.receipts
    RESULTS["stale_or_relayed_state_rejected"]=True

    # A direct message establishes contact, but the payload must be acknowledged.
    m.receive(d,message(d,0,2162),2162)
    tick(m,d,2162)
    assert m.phase==HOLD
    d.red_packet=(2163,())
    tick(m,d,2163)
    assert m.exchange_version==2163
    m.receive(d,message(d,0,2174,seen=2162,empty=(0,1,2,4)),2174)
    tick(m,d,2174)
    assert m.target==0 and not any(row[1]=="exchange_complete" for row in m.audit)
    m.receive(d,message(d,0,2175,seen=2163,empty=(0,1,2)),2175)
    tick(m,d,2175)
    assert m.target==0
    m.receive(d,message(d,0,2176,seen=2163,empty=(0,1,2,4)),2176)
    tick(m,d,2176)
    assert any(row[1]=="payload_ack" for row in m.audit)
    assert m.audit[-1][1]=="exchange_complete"
    RESULTS["bidirectional_map_and_empty_ack_required"]=True

    m,d=MessengerRun(),drone()
    d.states[0]["point"]=(10.,0.)
    activate(m,d)
    m.receive(d,message(d,0,2161),2161)
    tick(m,d,2161)
    d.red_packet=(2162,())
    for step in range(2162,2252):
        m.receive(d,message(d,0,step,empty=(0,1,2,4)),step)
        tick(m,d,step)
    assert m.audit[-1][1]=="exchange_timeout"
    assert not any(row[1]=="exchange_complete" for row in m.audit)
    RESULTS["unacknowledged_exchange_has_90_step_bound"]=True

    m,d=MessengerRun(),drone()
    d.states[0]["point"]=(10.,0.)
    activate(m,d)
    for step in range(2161,2282):
        tick(m,d,step)
    assert any(row[1]=="peer_skipped" for row in m.audit)
    assert not any(row[1]=="contact" for row in m.audit)
    RESULTS["stale_nearby_point_wait_is_reachable_and_bounded"]=True

    # Finishing the tour does not prevent delivery of a later empty report.
    m,d=MessengerRun(),drone()
    m.state=DONE
    m.known_empty={0,1,2,4}
    d.inventory_records[3]=(4000,0)
    tick(m,d,4001)
    assert m.state==ACTIVE and m.target==0 and m.delivery_only
    assert m.delivery_until==4201 and m.delivery_attempts==1
    d.inventory_records[3]=(4002,0)
    tick(m,d,4002)
    assert m.delivery_attempts==1
    d.communicator_is_disabled=lambda:True
    tick(m,d,4201)
    assert m.state==DONE
    tick(m,d,4202)
    assert m.state==DONE and m.delivery_attempts==1
    RESULTS["late_empty_wakes_once_and_budget_exits_even_in_no_com"]=True

    for step,wall in ((4001,172.),(5359,150.)):
        m,d=MessengerRun(),drone()
        m.state=DONE
        m.known_empty={0,1,2,4}
        d.inventory_records[3]=(step-1,0)
        d.elapsed_walltime=wall
        tick(m,d,step)
        assert m.state==DONE and m.delivery_attempts==0
    RESULTS["redelivery_respects_walltime_and_step_reserves"]=True

    m,d=MessengerRun(),drone()
    m.state=ACTIVE
    m.visited={0,1,2,3}
    m.known_empty={0,1,2,4}
    d.inventory_records[3]=(3000,0)
    tick(m,d,3001)
    assert m.target==0 and m.delivery_attempts==1
    RESULTS["new_empty_revisits_already_visited_receiver"]=True

    m,d=MessengerRun(),drone()
    tick(m,d,2159)
    assert m.state==IDLE
    d.identifier=2
    tick(m,d,2200)
    assert m.state==IDLE
    d.identifier=4
    d.previous_inventory=1
    tick(m,d,2200)
    assert m.state==IDLE
    RESULTS["fixed_identity_activation_and_empty_requirement_retained"]=True

class Flight(RedHooks):
    def __init__(self):
        self.identifier=4
        self.team_size=5
        self.elapsed_timestep=2204
        self.elapsed_walltime=75.
        self.limit,self.walltime_limit=5400,180.
        self.previous_inventory=0
        self.pending_drop=None
        self.submitted=False
        self.pose,self.heading=np.zeros(2),0.
        self.last_confirmed_drop_step=None
        self.closeout=NS(state=IDLE,tick=noop)
        self.grid=NS(pose_fixed=True)
        self._odometry_only=False
        self.observe_calls,self.cache_calls,self.base_calls=0,0,0
        self.memory=NS(observe=self.observe,packet=lambda:(None,np.zeros((2,2)),None,None),
                       free=np.ones((2,2)),hits=np.zeros((2,2)))
        self.fine_wall_coverage=NS(observe=noop,packet=lambda:None)
        self.submission_bearings=NS(observe=noop)
        self.pre_submit_scan=PreSubmitScan()
        self.red_packet=(2100,())
        self.map_revision={0:2100}
        self.states={0:dict(point=(10.,0.),health=25)}
        self.inventory_records={i:(2100,int(i==3)) for i in range(5)}
        self.messenger=MessengerRun()
        self.messenger.state=ACTIVE
        self.messenger.phase=HOLD
        self.messenger.target=0
        self.messenger.hold_left=12
        if candidate:
            self.messenger.contact_step=2200
            self.messenger.known_empty={0,1,2,4}
        self.deadline_submission=DeadlineSubmission()
        self.deadline_versions={}
        self.image=np.ones((2,2),dtype=np.uint8)
        self.deadline_submission.remember(2100,self.image)
        self.map_quality=8000
        self.sent=None

    def _sync_placement(self,step):
        pass

    def observe(self,*args):
        self.observe_calls+=1

    def _update_drop_hints(self,*args):
        pass

    def _prepare_map_cache(self,step):
        self.cache_calls+=1
        return self.image

    def lidar_values(self):
        return np.full(181,100.)

    def lidar_rays_angles(self):
        return np.linspace(-np.pi,np.pi,181)

    def semantic_values(self):
        return ()

    def communicator_is_disabled(self):
        return False

    def measured_velocity(self):
        return np.zeros(2)

    def drive(self,*args,**kwargs):
        return NAV.copy()

    def _submission_image(self,step):
        return self.image,None,{}

    def submit_exploration_map(self,image):
        self.sent=image.copy()

def base_control(d):
    d.base_calls+=1
    return NAV.copy()

with patch.object(LBBDRescue,"control",base_control):
    d=Flight()
    d.control()
    if candidate:
        assert d.observe_calls==d.cache_calls==1
        assert d.red_packet[0]==2204 and d.deadline_submission.backup_step==2204
        RESULTS["active_messenger_refreshes_map_and_submission_backup"]=True
    else:
        assert d.observe_calls==d.cache_calls==0 and d.red_packet[0]==2100
        RESULTS["active_messenger_refresh"]="baseline returns before refresh"
    for step,seconds,reason in ((2204,178.6,"walltime"),(5396,150.,"timestep")):
        d=Flight()
        d.elapsed_timestep,d.elapsed_walltime=step,seconds
        d.control()
        assert d.base_calls==0 and np.array_equal(d.sent,d.image)
        assert d.deadline_submission_event["fallback"]==reason
    RESULTS["dual_deadline_submission_precedes_messenger"]=True

print(json.dumps(dict(arm=args.arm,status="PASS",physics_steps=0,scenarios=RESULTS),indent=2))

