"""Global variable registry shared by all modules of the dispatch system.

Keys used by the system:
    "funds"              -> int
    "riders"             -> list[Rider]
    "rider_id_counter"   -> int
    "running"            -> bool
    "tick"               -> int
    "orders"             -> list[Order]
    "config"             -> dict
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
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)
