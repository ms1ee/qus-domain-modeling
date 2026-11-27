"""Global variable storage shared across the dispatch system.

Keys used by the system:
    "funds"            -> int, system funds (may become negative)
    "riders"           -> list[Rider]
    "rider_id_counter" -> int, last rider ID handed out
    "running"          -> bool, main loop flag
    "time"             -> int, simulated time in ticks
    "orders"           -> list[Order], every order ever created
    "config"           -> dict, active configuration
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
    """Return the value stored under ``key`` or ``default`` when absent."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` has been set."""
    return key in _global_dict
