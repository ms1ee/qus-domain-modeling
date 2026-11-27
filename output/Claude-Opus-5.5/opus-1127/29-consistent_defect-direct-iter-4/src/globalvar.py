"""Global variable storage shared across the dispatch system modules.

The module keeps a single dictionary that is used as a light-weight
registry for system wide values such as funds, the rider list, the
rider id counter, the simulated time and the order list.
"""

_global_dict = None


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    """Make sure the global dictionary exists (lazy initialisation)."""
    global _global_dict
    if _global_dict is None:
        _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key`` in the global dictionary."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    _ensure()
    return _global_dict.get(key, default)


def has_value(key):
    """Return True if ``key`` exists in the global dictionary."""
    _ensure()
    return key in _global_dict
