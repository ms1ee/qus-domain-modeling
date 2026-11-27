"""Process-wide key/value store shared by the simulator modules.

The store holds shared runtime objects such as the rider list (``"riders"``),
the simulated clock (``"simulated_time"``) and the system manager (``"system"``).
"""

_global_dict = {}


def _init():
    """Reset the global store to its initial state.

    After initialization the store contains an empty rider list under the key
    ``"riders"`` and a simulated clock set to 0 under ``"simulated_time"``.
    """
    global _global_dict
    _global_dict = {}
    _global_dict["riders"] = []
    _global_dict["simulated_time"] = 0


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable key identifying the global value.
        value: Any object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Key to look up.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is absent.
    """
    return _global_dict.get(key, default)


_init()
