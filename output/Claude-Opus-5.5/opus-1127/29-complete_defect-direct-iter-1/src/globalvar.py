"""Global variable store shared across the dispatch system modules.

Keys used by the system:
    "riders"            -> list[Rider]
    "rider_id_counter"  -> int
    "running"           -> bool
    "funds"             -> int
    "time"              -> int (current simulation tick)
    "orders"            -> list[Order]
    "config"            -> dict
"""

_global_dict = {}


def _init():
    """Initialise (reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a global value under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the global value stored under ``key`` (or ``default``)."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` exists in the global store."""
    return key in _global_dict
