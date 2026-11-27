"""Process-wide variable store shared by the dispatch simulator modules.

Keys used by the program:
    "riders"           list[Rider]  active riders
    "rider_id_counter" int          last issued rider id
    "funds"            int          system funds (may be negative)
    "running"          bool         main loop control flag
    "tick"             int          simulated time in ticks
    "orders"           list[Order]  order history
    "pending_orders"   list[Order]  orders waiting for a rider
    "grid"             dict         description of the grid map
"""

from __future__ import annotations

from typing import Any

_global_dict: dict[str, Any] = {}


def _init() -> None:
    """Reset the variable store to its default contents."""
    global _global_dict
    _global_dict = {
        "riders": [],
        "rider_id_counter": 0,
        "funds": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "pending_orders": [],
        "grid": {},
    }


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Variable name.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Fetch a value from the store.

    Args:
        key: Variable name.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
