"""Process-wide key/value store for shared simulation state.

Keys used by the program:
    "riders"          -> list[Rider] of all active riders
    "orders"          -> list[Order] of all orders (active and completed)
    "order_history"   -> list[OrderRecord] of completed orders
    "current_tick"    -> int simulated time
    "next_order_id"   -> int auto-increment counter for orders
    "speed_options"   -> tuple of rider speeds (units per tick)
    "rider_capacity"  -> max number of simultaneous orders per rider
    "load_penalty"    -> distance penalty per assigned order in assignment
"""

_global_dict = {}


def _init():
    """Reset the global store to its default contents.

    This function is called on import and again by ``system.init_system``.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "orders": [],
        "order_history": [],
        "current_tick": 0,
        "next_order_id": 1,
        "speed_options": (10, 15, 20),
        "rider_capacity": 2,
        "load_penalty": 150,
    }


def set_value(key, value):
    """Store a value under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a global value.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is not present.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
