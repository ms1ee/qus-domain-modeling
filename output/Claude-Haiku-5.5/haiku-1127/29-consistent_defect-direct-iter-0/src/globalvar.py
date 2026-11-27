"""Process-wide key/value store shared by the simulator modules.

Keys used by the program:
    "system_funds"      int, current system funds (may be negative)
    "riders"            list[Rider], dynamic rider list
    "rider_id_counter"  int, last issued rider id
    "order_id_counter"  int, last issued order id
    "orders"            list[Order], every order created in this session
    "running"           bool, controls the main loop
    "tick"              int, simulated time (one unit per tick)
    "config"            dict, configurable system parameters
"""

from copy import deepcopy

DEFAULT_CONFIG = {
    "initial_funds": 1000,       # starting system funds
    "recruit_min_funds": 300,    # funds required before recruiting
    "recruit_cost": 500,         # cost deducted per recruited rider
    "rider_speed": 20,           # units per tick for newly created riders
    "rider_spawn": [400, 400],   # spawn location of new riders
}

_store = {}


def _init():
    """Reset the global store to its default values.

    Called once at startup (and again by ``system.init_system``).
    """
    global _store
    _store = {
        "system_funds": DEFAULT_CONFIG["initial_funds"],
        "riders": [],
        "rider_id_counter": 0,
        "order_id_counter": 0,
        "orders": [],
        "running": True,
        "tick": 0,
        "config": deepcopy(DEFAULT_CONFIG),
    }


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Global variable name.
        value: Any Python object.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` when missing.

    Args:
        key: Global variable name.
        default: Value returned when the key does not exist.

    Returns:
        The stored value or ``default``.
    """
    return _store.get(key, default)


_init()
