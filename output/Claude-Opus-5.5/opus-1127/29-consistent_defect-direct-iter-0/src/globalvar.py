"""Global variable store shared across the dispatch system modules.

Usage::

    import globalvar
    globalvar._init()
    globalvar.set_value("riders", [])
    riders = globalvar.get_value("riders")
"""

_global_dict = {}


def _init():
    """(Re)initialise the global variable dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (``default`` if missing)."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is present in the global store."""
    return key in _global_dict


def all_values():
    """Return a shallow copy of the whole global store."""
    return dict(_global_dict)
