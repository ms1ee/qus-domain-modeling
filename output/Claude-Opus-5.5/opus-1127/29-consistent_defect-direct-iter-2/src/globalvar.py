"""Global variable storage shared across modules.

Keys used by the program:
    "money"            -> int, system funds (may be negative)
    "riders"           -> list[Rider]
    "rider_id_counter" -> int, last allocated rider id
    "running"          -> bool, main loop flag
    "orders"           -> list[Order], all orders created
    "time"             -> int, current simulated tick
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a global value, returning ``default`` when missing."""
    return _global_dict.get(key, default)
