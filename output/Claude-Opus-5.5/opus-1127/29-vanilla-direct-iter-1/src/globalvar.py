"""Global variable storage shared across modules.

Keys used by the system:
    "funds"              -> int, system funds (may become negative)
    "riders"             -> list[Rider]
    "rider_id_counter"   -> int, last issued rider id
    "running"            -> bool, main loop flag
    "time"               -> int, current simulation tick
    "orders"             -> list[Order], all orders ever created
    "pending_orders"     -> list[Order], orders waiting for a rider
"""

_global_dict = {}


def _init():
    """Initialise (reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a global value (``default`` if missing)."""
    return _global_dict.get(key, default)
