"""Process-wide global variable store.

The store holds the core system data: system funds, the rider list, the rider
ID counter, the running flag, the simulated clock and the order list.
"""

from config import SETTINGS

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    Default keys:
        funds: System funds (integer, may become negative).
        riders: List of Rider objects (key "riders").
        rider_id_counter: Last issued rider ID.
        running: Main loop running flag.
        tick: Current simulated time.
        orders: List of every Order created in this session.
    """
    global _global_dict
    _global_dict = {
        "funds": SETTINGS["initial_funds"],
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
    }


def set_value(key, value):
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.

    Returns:
        The stored value, or None if the key does not exist.
    """
    return _global_dict.get(key)


_init()
