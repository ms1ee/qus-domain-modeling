"""Process-wide key/value store holding the simulator's global variables.

Keys used by the program:
    system_funds (int), riders (list[Rider]), rider_id_counter (int),
    system_running (bool), tick (int), orders (list[Order]),
    pending_orders (list[Order]), rider_speed (int), recruit_cost (int).
"""

from grid import DEFAULT_RIDER_SPEED, INITIAL_FUNDS, RECRUIT_COST

_store = {}


def _init() -> None:
    """Reset every global variable to its startup default value."""
    global _store
    _store = {
        "system_funds": INITIAL_FUNDS,
        "riders": [],
        "rider_id_counter": 0,
        "system_running": True,
        "tick": 0,
        "orders": [],
        "pending_orders": [],
        "rider_speed": DEFAULT_RIDER_SPEED,
        "recruit_cost": RECRUIT_COST,
    }


def set_value(key, value) -> None:
    """Store a value under the given key.

    Args:
        key: Variable name.
        value: Value to store.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under key, or default if absent.

    Args:
        key: Variable name.
        default: Value returned when the key is missing.

    Returns:
        The stored value.
    """
    return _store.get(key, default)


_init()
