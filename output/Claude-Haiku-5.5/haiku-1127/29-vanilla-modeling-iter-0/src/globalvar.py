"""Process-wide key/value store for the food delivery dispatch simulator.

The store holds the runtime "global variables" described in the PRD:
system funds, the rider list (key ``"riders"``), the rider ID counter,
the running flag, the simulated clock and the order collections.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to the default system state.

    Defaults:
        funds: 1000
        riders: empty list
        rider_id_counter: 0
        is_running: True
        simulated_time: 0
        pending_orders: empty list
        orders: empty list
    """
    _store.clear()
    _store.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "is_running": True,
            "simulated_time": 0,
            "pending_orders": [],
            "orders": [],
        }
    )


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
        The stored value, or ``default`` if the key does not exist.
    """
    return _store.get(key, default)


_init()
