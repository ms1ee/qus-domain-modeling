"""Process-wide key/value storage shared by the dispatch simulator modules.

The store holds the global system variables described in the PRD, such as
the system funds, the rider list (key ``"riders"``), the rider ID counter,
the running flag, the simulated tick and the order history.
"""

_global_dict = {}


def _init():
    """Reset the global variable store to an empty dictionary.

    Called at import time and by ``system.init_system`` to start from a
    clean state.
    """
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable identifier of the global variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Identifier of the global variable.
        default: Value returned when ``key`` has not been set.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
