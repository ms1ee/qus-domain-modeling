"""Process-wide global variable store.

Holds the shared system state (funds, rider list, rider ID counter, running
flag, simulated tick, order records). Access it through ``set_value`` and
``get_value`` so that all modules see the same values.
"""

import config

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    Keys created:
        riders: list of Rider objects (dynamic rider pool).
        funds: integer system funds (may become negative).
        rider_id_counter: last issued rider ID (0 at startup).
        running: boolean main-loop control flag.
        tick: current simulated time in ticks.
        orders: list of every Order accepted into the system.
        order_history: list of completed Order objects.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "funds": config.INITIAL_FUNDS,
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "order_history": [],
    }


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
