"""Global variable store shared across the dispatch system modules.

Keys used by the system:
    funds              -> int
    riders             -> list[Rider]
    rider_id_counter   -> int
    running            -> bool
    tick               -> int
    orders             -> list[Order]
    config             -> Configuration
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default`` if missing)."""
    return _global_dict.get(key, default)
