"""Avoid freezing a demonstrably partial map until the fallback can compare alternatives."""

def provisional_map(step, estimate, peer_revisions, wall_seconds_left):
    if estimate is None or estimate >= 5000 or wall_seconds_left <= 12.:
        return False
    return not any(0 <= step - stamp < 600 for stamp in peer_revisions.values())
