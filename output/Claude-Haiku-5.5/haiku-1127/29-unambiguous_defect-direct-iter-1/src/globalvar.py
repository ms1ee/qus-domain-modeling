"""Global variable store shared by all simulator modules.

Keys used by the program:
    "funds"            -- integer system funds (may be negative)
    "riders"           -- list[Rider] of active riders
    "rider_id_counter" -- last issued rider id
    "running"          -- boolean main-loop flag
    "tick"             -- current simulated time
    "orders"           -- list[Order] of all orders created so far
"""

_global_dict = {}


def _init():
    """Reset the global variable store to an empty dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)
