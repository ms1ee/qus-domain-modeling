"""Global variable store shared by all modules of the simulator.

Keys used by the system include:
    "funds", "riders" (list[Rider]), "rider_id_counter", "running",
    "tick", "orders", "order_id_counter", "recruitment_cost",
    "max_riders", "rider_speed", "config".
"""

_global_dict = None


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default``)."""
    if _global_dict is None:
        _init()
    return _global_dict.get(key, default)
