"""Process-wide global variable store.

Holds system funds, the rider list, ID counters, the running flag and the
simulated clock. Access is through set_value / get_value.
"""

_global_dict = {}


def _init():
    """Reset the global store and create the default rider list.

    Called at import time and by system.init_system().
    """
    global _global_dict
    _global_dict = {}
    _global_dict["riders"] = []


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Global variable name.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key):
    """Return the value stored under key, or None if it is absent.

    Args:
        key: Global variable name.

    Returns:
        The stored value or None.
    """
    return _global_dict.get(key)


_init()
