"""Global variable store shared across all modules of the dispatch system.

Usage::

    import globalvar
    globalvar._init()
    globalvar.set_value("riders", [])
    riders = globalvar.get_value("riders")
"""

_global_dict = None


def _init():
    """(Re)initialise the global dictionary, discarding any previous values."""
    global _global_dict
    _global_dict = {}


def is_initialized():
    """Return True when the global store has been initialised."""
    return _global_dict is not None


def set_value(key, value):
    """Store ``value`` under ``key``. Initialises the store lazily if needed."""
    global _global_dict
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    if _global_dict is None:
        return default
    return _global_dict.get(key, default)


def keys():
    """Return a list of all keys currently stored."""
    if _global_dict is None:
        return []
    return list(_global_dict.keys())
