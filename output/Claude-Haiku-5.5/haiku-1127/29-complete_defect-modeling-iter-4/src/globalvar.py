"""Process-wide storage for shared simulation state.

Keys used across the program:
    "funds"            int, system funds (may be negative)
    "rider_id_counter" int, last rider ID handed out
    "running"          bool, main loop control flag
    "simulated_time"   int, current simulated tick
    "riders"           list[Rider], all active riders
    "config"           SystemConfig instance
    "grid"             GridMap instance
    "path_planner"     PathPlanner instance
    "order_manager"    OrderManager instance
    "system_manager"   SystemManager instance
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset every global variable to its startup default value."""
    _store.clear()
    _store.update({
        "funds": 0,
        "rider_id_counter": 0,
        "running": True,
        "simulated_time": 0,
        "riders": [],
        "config": None,
        "grid": None,
        "path_planner": None,
        "order_manager": None,
        "system_manager": None,
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
        The stored value, or ``default`` if the key does not exist.
    """
    return _store.get(key, default)


_init()
