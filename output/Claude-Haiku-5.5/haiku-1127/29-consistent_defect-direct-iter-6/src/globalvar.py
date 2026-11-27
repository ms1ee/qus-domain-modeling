"""Process-wide key/value store for the food delivery dispatch simulator.

The store holds the system funds, the rider list (key ``"riders"``), the rider
ID counter, the running flag, the simulated tick counter and the order history.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Defaults:
        system_funds: 1000
        riders: empty list
        rider_id_counter: 0
        running: True
        tick: 0
        orders: empty list
    """
    _store.clear()
    _store.update({
        "system_funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
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
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)


_init()
