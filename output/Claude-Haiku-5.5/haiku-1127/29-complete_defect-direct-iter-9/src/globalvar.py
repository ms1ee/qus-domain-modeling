"""Process-wide global variable store.

Values are kept in a module-level dictionary. The key ``"riders"`` holds the
``list[Rider]`` of all active riders.
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global variable dictionary.

    Creates the default entries, including an empty ``"riders"`` list.
    """
    global _global_dict
    _global_dict = {"riders": []}


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a global variable.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
