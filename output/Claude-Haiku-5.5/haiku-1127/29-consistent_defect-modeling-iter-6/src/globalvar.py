"""Process-wide global variable store.

This module keeps the shared system state (funds, riders, orders, clock and
run flag) in a single dictionary so that the different modules of the
dispatch simulator can access the same objects without circular imports.
"""

from typing import Any, Optional

_global_dict: dict = {}


def _init() -> None:
    """Initialise the global store with the default system parameters.

    Sets system funds to 1000, an empty rider list, the rider ID counter to 0,
    the running flag to True, the simulated clock to 0 and the default
    recruitment parameters.
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "rider_id_counter": 0,
        "is_running": True,
        "current_time": 0,
        "riders": [],
        "orders": [],
        "recruit_cost": 500,
        "min_recruit_funds": 300,
    }


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable (for example ``"riders"``).
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Optional[Any] = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)
