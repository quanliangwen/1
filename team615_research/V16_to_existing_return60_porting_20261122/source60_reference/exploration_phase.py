"""PJ01 normal-exploration phase alignment, no waiting or task assignment.

The original due predicate always wins. Only an existing ordinary exploration
route may be reconsidered early; sensing, motion, communication, placement,
budget and submission execute through the original controller every frame.
"""
def exploration_route_due(step,last_plan_step,identifier,team_size,*,ordinary_exploration,period=24):
    original_due=step-last_plan_step>=period
    if (not ordinary_exploration or original_due or last_plan_step<0
        or last_plan_step>=step or not isinstance(identifier,int)
        or not isinstance(team_size,int) or not isinstance(period,int)
        or not 1<=team_size<=period or not 0<=identifier<team_size):
        return original_due
    phase=(period*identifier)//team_size
    next_slot=last_plan_step+1+(phase-(last_plan_step+1))%period
    return step>=next_slot

def ordinary_exploration_scope(drone,step,returning):
    if (returning or getattr(drone,'submitted',False)
        or getattr(drone,'coverage_ready',True)
        or getattr(drone,'_seeking_fusion',False)
        or step<getattr(drone,'escape_until',-1)
        or getattr(drone,'assignment_goal',None)is not None
        or getattr(drone,'placement_goal',None)is not None
        or getattr(drone,'pending_drop',None)is not None
        or getattr(drone,'goal',None)is None
        or not getattr(drone,'waypoints',None)):
        return False
    if not hasattr(drone,'carried_bombs_count')or not hasattr(drone,'_remaining_steps'):
        return False
    if drone.carried_bombs_count()<=0 or drone._remaining_steps()<=24.:
        return False
    # A received directed survey is an existing task, not a free frontier bid.
    plan=getattr(drone,'survey_plan',None)
    if isinstance(plan,(tuple,list))and len(plan)==5:
        epoch,sender,owner,point,until=plan
        if (owner==int(drone.identifier or 0)and point is not None
            and 0<=step-epoch<120 and step<until):
            return False
    return True

def early_exploration_due(drone,step,returning):
    return exploration_route_due(step,drone.last_plan_step,int(drone.identifier or 0),
        int(getattr(drone,'team_size',1)),ordinary_exploration=ordinary_exploration_scope(drone,step,returning))
