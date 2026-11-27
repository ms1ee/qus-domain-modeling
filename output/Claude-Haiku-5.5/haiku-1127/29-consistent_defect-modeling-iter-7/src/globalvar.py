"""Process-wide key/value storage shared by the simulator modules.

The simulator keeps its shared state (funds, riders, orders, clock) in a
single dictionary so that every module can reach it through ``get_value``
and ``set_value`` without creating circular imports.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global storage to its default layout.

    The list containers used across modules are always created here so that
    ``get_value("riders")`` and ``get_value("orders")`` return lists.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "orders": [],
        "current_tick": 0,
        "running": True,
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
        The stored value, or ``default``.
    """
    return _global_dict.get(key, default)


_init()
