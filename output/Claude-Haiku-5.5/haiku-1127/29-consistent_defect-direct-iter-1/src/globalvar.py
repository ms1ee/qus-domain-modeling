"""Process-wide key/value store used for shared simulation state.

Keys used by the program:
    funds (int), riders (list[Rider]), rider_id_counter (int),
    running (bool), tick (int), orders (list[Order]),
    order_id_counter (int).
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the store to its default values.

    Sets system funds to 1000, an empty rider list, the rider ID counter to 0,
    the running flag to True, the simulated tick to 0 and an empty order list.
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "order_id_counter": 0,
    }


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
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


def current_tick() -> int:
    """Return the current simulated tick as an integer.

    Returns:
        The value of the ``tick`` variable, or 0 if it is not set.
    """
    value = _global_dict.get("tick", 0)
    return int(value) if value is not None else 0


_init()
