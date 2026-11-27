"""Process-wide global variable store.

Values are kept in a module-level dictionary. ``_init`` resets the store and
creates the default entries: ``"riders"`` (a list of Rider objects) and
``"current_tick"`` (the simulated time counter).
"""

_global_dict = {}


def _init():
    """(Re)initialise the global store with default values.

    The ``"riders"`` key is set to an empty list and ``"current_tick"`` to 0.
    """
    global _global_dict
    _global_dict = {"riders": [], "current_tick": 0}


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global entry (for example ``"riders"``).
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global entry.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_dict.get(key, default)


def get_current_tick():
    """Return the current simulated tick as an integer.

    Returns:
        int: The value of the ``"current_tick"`` entry, or 0 if unset.
    """
    value = _global_dict.get("current_tick", 0)
    return int(value or 0)
