"""Global variable store shared by all modules of the dispatch simulator.

Typical keys:
    "riders"            -> list[Rider]
    "rider_id_counter"  -> int
    "order_id_counter"  -> int
    "running"           -> bool
    "funds"             -> int
    "tick"              -> int
    "orders"            -> list[Order]   (all orders ever created)
    "pending_orders"    -> list[Order]   (orders waiting for a rider)
    "config"            -> Configuration
"""

_global_dict = None


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    """Make sure the global dictionary exists."""
    if _global_dict is None:
        _init()


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (``default`` if missing)."""
    _ensure()
    return _global_dict.get(key, default)


def has_key(key):
    """Return True when ``key`` is present in the store."""
    _ensure()
    return key in _global_dict


def keys():
    """Return a list of all stored keys."""
    _ensure()
    return list(_global_dict.keys())
