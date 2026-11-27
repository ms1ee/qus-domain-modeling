"""Global variable store shared by the food delivery dispatch simulator.

The store is a plain dictionary that is repopulated by ``_init``. Keys used
by the program include ``"riders"`` (list of Rider objects), ``"funds"``,
``"rider_id_counter"``, ``"is_running"``, ``"current_tick"``, ``"orders"``,
``"pending_orders"``, ``"completed_orders"``, ``"config"`` and ``"system"``.
"""

from typing import Any

_global_dict: dict = {}


def _init() -> None:
    """Reset the global store to its default values.

    Populates the empty rider list, the rider ID counter, zero funds, the
    running flag, the simulated clock and the order containers.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "rider_id_counter": 0,
        "funds": 0,
        "is_running": True,
        "current_tick": 0,
        "orders": [],
        "pending_orders": [],
        "completed_orders": [],
        "config": None,
        "system": None,
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
