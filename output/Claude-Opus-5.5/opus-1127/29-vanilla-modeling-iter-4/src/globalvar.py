"""Global variable store shared by all modules of the dispatch simulator.

Keys used by the system:
    "funds"             -> int
    "riders"            -> list[Rider]
    "rider_id_counter"  -> int
    "running"           -> bool
    "tick"              -> int
    "orders"            -> list[Order]
    "order_id_counter"  -> int
    "config"            -> dict
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


def has_value(key):
    """Return True if ``key`` has been set."""
    return key in _global_dict
