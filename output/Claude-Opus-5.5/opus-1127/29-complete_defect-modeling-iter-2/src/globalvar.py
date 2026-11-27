"""Global variable registry shared across the dispatch system.

Typical keys:
    "riders"            -> list[Rider]
    "orders"            -> list[Order]
    "funds"             -> int
    "rider_id_counter"  -> int
    "running"           -> bool
    "tick"              -> int
"""

_global_dict = {}


def _init():
    """(Re)initialise the global registry to an empty dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default`` if missing)."""
    return _global_dict.get(key, default)
