"""Process-wide key/value store shared by the dispatch simulator modules.

The store holds the rider list (key ``"riders"``), the order list
(``"orders"``), the system funds, ID counters, the running flag, the
simulation tick, and the loaded configuration.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    After this call the rider list is empty, the rider and order ID counters
    are zero, the running flag is True, and the tick is 0. Funds are set to 0
    here and overwritten by ``system.init_system``.
    """
    _store.clear()
    _store.update({
        "riders": [],
        "orders": [],
        "completed_orders": [],
        "funds": 0,
        "rider_id_counter": 0,
        "order_id_counter": 0,
        "running": True,
        "tick": 0,
        "config": {},
        "rng": None,
    })


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _store.get(key, default)


def next_id(counter_key: str) -> int:
    """Increment the counter stored under ``counter_key`` and return it.

    Args:
        counter_key: Name of an integer counter in the store.

    Returns:
        The new counter value (first call returns 1).
    """
    value = int(_store.get(counter_key, 0)) + 1
    _store[counter_key] = value
    return value


_init()
