"""Process-wide global variable store.

Holds shared runtime values such as the rider list and the current tick so
that modules can access them without circular imports.
"""

_global_dict: dict = {}


def _init() -> None:
    """(Re)initialise the global variable store with default values.

    Sets up the rider list, the simulated clock and the running flag.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "current_tick": 0,
        "running_state": True,
    }


def set_value(key, value) -> None:
    """Store a value under the given key.

    Args:
        key: Variable name, e.g. "riders".
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a value from the global store.

    Args:
        key: Variable name.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
