"""Process-wide global variable store.

The store is a simple dictionary shared by the simulator modules. It holds
shared references such as the rider list (key ``"riders"``) and the simulated
clock (key ``"current_tick"``).
"""

_global_dict = {}


def _init():
    """Reset the global variable dictionary to an empty state."""
    global _global_dict
    _global_dict = {}


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
        default: Value returned when ``key`` is not present.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


def current_tick():
    """Return the current simulated tick as an integer (0 if unset)."""
    return get_value("current_tick") or 0
