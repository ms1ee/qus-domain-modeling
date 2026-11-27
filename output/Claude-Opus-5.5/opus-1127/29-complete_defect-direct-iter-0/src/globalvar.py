"""Global variable store shared across the dispatch system modules.

Keys used by the system:
    "funds"             -> int, system fund balance (may be negative)
    "riders"            -> list[Rider]
    "rider_id_counter"  -> int, last rider id handed out
    "running"           -> bool, main loop control flag
    "orders"            -> list[Order], full order history
    "time"              -> int, simulated time (ticks)
    "config"            -> dict, system parameters
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)


def has_value(key):
    """Return True when ``key`` has been set."""
    return key in _global_dict
