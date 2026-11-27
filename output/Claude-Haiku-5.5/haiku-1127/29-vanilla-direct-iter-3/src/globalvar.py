"""Process-wide global variable store.

The store is a simple dictionary wrapped by ``set_value`` / ``get_value``.
Keys used by the program:

    funds            (int)        system fund balance, may be negative
    riders           (list)       list of Rider objects (key "riders")
    rider_id_counter (int)        last rider ID handed out
    running          (bool)       main loop control flag
    time             (int)        simulated time in ticks
    orders           (list)       every Order ever created
    pending_orders   (list)       orders not yet assigned to a rider
    completed_orders (list)       orders that have been delivered
    config           (dict)       system parameters loaded at start-up
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset every global variable to its start-up default value."""
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
        "pending_orders": [],
        "completed_orders": [],
        "config": {},
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


# Make the store usable immediately after import.
_init()
