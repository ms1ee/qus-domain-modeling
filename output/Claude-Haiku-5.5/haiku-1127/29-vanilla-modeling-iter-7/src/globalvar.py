"""Global variable storage shared across the dispatch simulator.

Values live in a module-level dictionary so that any module can read or
write shared state (system funds, the rider list, the current tick, ...)
without passing references around explicitly.
"""

_global_dict = {}


def _init():
    """Reset the global store and create the default keys.

    Must be called once at system startup before other modules access
    shared state.
    """
    global _global_dict
    _global_dict = {"riders": []}


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
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)
