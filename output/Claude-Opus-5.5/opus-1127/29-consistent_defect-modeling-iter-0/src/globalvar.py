"""Global variable registry shared across modules.

Usage::

    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.get_value("riders")
"""

_global_dict = None


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    if _global_dict is None:
        _init()


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value for ``key`` or ``default`` if it is missing."""
    _ensure()
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` has been set."""
    _ensure()
    return key in _global_dict


def keys():
    """Return a list of all registered keys."""
    _ensure()
    return list(_global_dict.keys())
