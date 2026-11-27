"""Process-wide variable store shared by the dispatch simulator.

Values live in a module-level dictionary so that every module can read and
write shared state (funds, riders, orders, simulated time) without creating
circular imports. Call :func:`_init` to reset the store to default values.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to the default system values.

    Defaults:
        funds: 1000
        riders: empty list
        rider_id_counter: 0
        running: True
        simulated_time: 0
        orders: empty list
    """
    _store.clear()
    _store.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "running": True,
            "simulated_time": 0,
            "orders": [],
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable, e.g. ``"riders"``.
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
