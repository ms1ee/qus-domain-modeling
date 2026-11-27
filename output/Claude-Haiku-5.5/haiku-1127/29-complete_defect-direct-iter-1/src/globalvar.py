"""Global variable storage shared by the dispatch simulator modules.

The storage holds the core system data: system funds, the rider list, the
rider ID counter, the running flag, the simulated tick, and order lists.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global storage to its default values.

    Defaults:
        riders: empty list.
        rider_id_counter: 0.
        funds: 0.
        running: True.
        tick: 0.
        orders / pending_orders / completed_orders: empty lists.
        order_id_counter: 0.
    """
    _store.clear()
    _store.update({
        "riders": [],
        "rider_id_counter": 0,
        "funds": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "pending_orders": [],
        "completed_orders": [],
        "order_id_counter": 0,
    })


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _store.get(key, default)
