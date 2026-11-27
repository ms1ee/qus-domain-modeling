"""Process-wide key/value store shared by all dispatch modules.

The store holds the system funds, the rider list, the rider ID counter,
the running flag, the simulated clock, and the order records.
"""

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    Creates an empty rider list, a zero rider ID counter, the running flag
    set to True, a zeroed simulated clock, and an empty order list.
    """
    global _global_dict
    _global_dict = {
        "funds": 5000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "order_counter": 0,
        "orders": [],
        "recruit_cost": 500,
        "max_riders": 20,
        "config": {},
    }


def set_value(key, value):
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: The name of the global variable.
        value: The value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: The name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
