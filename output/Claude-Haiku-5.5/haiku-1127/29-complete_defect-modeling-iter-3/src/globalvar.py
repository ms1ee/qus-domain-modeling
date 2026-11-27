"""Global variable storage shared by the dispatch simulator modules.

The module keeps one dictionary of named values. Other modules read and
write values through :func:`get_value` and :func:`set_value`. The
:func:`_init` function resets the store to the default configuration.
"""

from typing import Any, Dict

DEFAULT_PARAMETERS: Dict[str, int] = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "delivery_fee": 100,
    "rider_speed": 10,
    "max_orders_per_rider": 3,
    "max_ticks_per_order": 10000,
    "stall_limit": 3,
}

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Sets system funds, the rider ID counter, the running flag, the simulated
    tick counter, an empty rider list and all configurable parameters.
    """
    global _global_dict
    _global_dict = {
        "funds": DEFAULT_PARAMETERS["initial_funds"],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "riders": [],
    }
    _global_dict.update(DEFAULT_PARAMETERS)


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _global_dict.get(key, default)
