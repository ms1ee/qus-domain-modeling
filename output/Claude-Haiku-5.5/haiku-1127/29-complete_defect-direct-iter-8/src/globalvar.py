"""Global variable store shared by the dispatch simulator modules.

The store is a plain dictionary accessed through :func:`set_value` and
:func:`get_value`. Calling :func:`_init` restores every key to its default.

Keys used by the program:
    riders           list of Rider objects (dynamic CRUD list)
    rider_id_counter int, last rider ID handed out
    funds            int, system fund balance (may be negative)
    running          bool, controls the main loop
    tick             int, simulated time (one tick per loop iteration)
    orders           list of Order objects
    config           dict of system parameters
"""

from typing import Any, Dict

_DEFAULT_CONFIG: Dict[str, int] = {
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "order_fee": 150,
    "rider_speed": 50,
    "max_orders_per_rider": 3,
}

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    After this call the rider list is empty, the rider ID counter is 0,
    funds are 0, the running flag is True, the tick is 0, the order list
    is empty and the configuration holds the default parameters.
    """
    global _store
    _store = {
        "riders": [],
        "rider_id_counter": 0,
        "funds": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "config": dict(_DEFAULT_CONFIG),
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _store.get(key, default)


_init()
