"""Process-wide key/value store shared by the dispatch modules.

Interface:
    _init()                    reset the store to its startup defaults
    set_value(key, value)      store a value under ``key``
    get_value(key, default)    fetch a value (``default`` if the key is absent)

The rider list is stored under the key ``"riders"`` as ``list[Rider]``.
"""

from __future__ import annotations

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to the default system values.

    Sets system funds to 1000, an empty rider list, the rider ID counter to 0,
    the running flag to True, an empty order history and the clock to tick 0.
    """
    global _global_dict
    _global_dict = {
        "system_funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "system_running": True,
        "orders": [],
        "current_tick": 0,
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
