"""Global variable store shared across the dispatch simulator.

Keys used by the system:
    "riders"  -> list of Rider objects
    "orders"  -> list of Order objects
    "tick"    -> current simulated time (int)
    "system"  -> SystemManager instance
"""

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    The dictionary object itself is kept so that existing references remain valid.
    """
    _global_dict.clear()
    _global_dict["riders"] = []
    _global_dict["orders"] = []
    _global_dict["tick"] = 0
    _global_dict["rider_id_counter"] = 0
    _global_dict["is_running"] = True


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Variable name.
        value: Any Python object.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Variable name.
        default: Value returned when the key does not exist.

    Returns:
        The stored value or ``default``.
    """
    return _global_dict.get(key, default)


_init()
