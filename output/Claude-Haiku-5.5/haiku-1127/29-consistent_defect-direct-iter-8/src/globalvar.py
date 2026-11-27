"""Process-wide key/value store for shared simulation state.

The store is a simple module-level dictionary. ``_init()`` resets it to the
default values and is called automatically when the module is first imported
and again by ``system.init_system()``.

Well-known keys:
    system_funds      -- int, current fund balance (may be negative)
    riders            -- list[Rider], dynamic rider pool
    rider_id_counter  -- int, last issued rider ID
    system_running    -- bool, controls the main loop
    orders            -- list[Order], full order history
    pending_orders    -- list[Order], orders waiting for a rider
    sim_time          -- int, current simulation tick
    config            -- dict, system parameters
"""

from __future__ import annotations

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Sets system funds to 1000, an empty rider list, rider ID counter to 0,
    the running flag to True, and the simulation clock to tick 0.
    """
    global _global_dict
    _global_dict = {
        "system_funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "system_running": True,
        "orders": [],
        "pending_orders": [],
        "sim_time": 0,
        "config": {},
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _global_dict.get(key, default)


_init()
