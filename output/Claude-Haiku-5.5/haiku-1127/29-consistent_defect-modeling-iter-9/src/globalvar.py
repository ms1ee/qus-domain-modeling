"""Process-wide key/value store shared between simulator modules.

Interface:
    _init()                 -- reset the store to its default values
    set_value(key, value)   -- store ``value`` under ``key``
    get_value(key)          -- fetch the value stored under ``key``

Well-known keys:
    "funds"             int, system funds (may be negative)
    "riders"            list[Rider], dynamic rider list
    "rider_id_counter"  int, last issued rider id
    "is_running"        bool, main loop control flag
    "current_tick"      int, simulated time
"""

from typing import Any, Dict

_global_vars: Dict[str, Any] = {}


def _init() -> None:
    """Reset all global variables to their startup defaults."""
    global _global_vars
    _global_vars = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_vars[key] = value


def get_value(key: str) -> Any:
    """Return the value stored under ``key`` or ``None`` if absent.

    Args:
        key: Name of the global variable.

    Returns:
        The stored value, or None.
    """
    return _global_vars.get(key)


_init()
