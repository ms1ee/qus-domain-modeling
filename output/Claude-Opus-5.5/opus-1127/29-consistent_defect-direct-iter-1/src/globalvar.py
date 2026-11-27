"""Global variable store shared by all modules of the dispatch simulator.

Well-known keys:
    "funds"            -> int, system funds (may become negative)
    "riders"           -> list[Rider]
    "rider_id_counter" -> int, last rider id handed out
    "running"          -> bool, main loop flag
    "time"             -> int, current simulation tick
    "orders"           -> list[Order], every order ever created
"""

_global_dict = {}


def _init():
    """Reset the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default``."""
    return _global_dict.get(key, default)
