"""Global variable management for the dispatch simulator.

All shared simulation state (funds, riders, orders, tick, ...) is stored in
a single module-level dictionary so every module sees the same values.
"""

_global_dict = None


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    """Lazily initialise the global dictionary if needed."""
    if _global_dict is None:
        _init()


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default``)."""
    _ensure()
    return _global_dict.get(key, default)


def has_value(key):
    """Return True if ``key`` has been set."""
    _ensure()
    return key in _global_dict
