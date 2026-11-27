"""Process-wide key/value store shared by the simulator modules.

Keys used by the program:
    "riders"            list[Rider]  all active riders (dynamic list)
    "rider_id_counter"  int          last issued rider id
    "running"           bool         main loop control flag
    "time"              int          current simulated tick
    "funds"             int          system fund balance (may be negative)
    "orders"            list[Order]  order history
    "order_counter"     int          last issued order id
    "config"            dict         system parameters
"""

from typing import Any

_store: dict = {}


def _init() -> None:
    """Reset the global store to its default values."""
    global _store
    _store = {
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "funds": 0,
        "orders": [],
        "order_counter": 0,
        "config": {},
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key`` or ``default`` if absent.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value or the default.
    """
    return _store.get(key, default)


_init()
