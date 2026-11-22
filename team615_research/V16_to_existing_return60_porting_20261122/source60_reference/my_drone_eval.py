from swarm_rescue.solutions.red_hooks import RedHooks


def drone_class_for_mode(mode):
    if str(mode).lower() != "place":
        raise ValueError("Red placement mode required")
    return RedHooks
