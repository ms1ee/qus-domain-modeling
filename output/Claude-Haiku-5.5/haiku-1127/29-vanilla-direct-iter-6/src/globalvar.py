"""Global variable store for the food delivery dispatch simulator.

This module keeps a single process-wide dictionary of system-level values
such as system funds, the rider list, the rider ID counter, the running
flag and the simulated tick counter. Other modules access these values via
``get_value`` and ``set_value``.
"""

from typing import Any

_GLOBALS: dict = {}


def _init() -> None:
    """Reset all global variables to their default values.

    Defaults:
        funds: 1000 (used for rider recruitment and operating costs).
        riders: empty list of Rider objects.
        rider_id_counter: 0 (riders receive IDs 1, 2, 3, ...).
        running: True (controls the main execution loop).
        tick: 0 (simulated time, one unit per tick).
        orders: empty list of Order objects (full order history).
        grid_size: 800 (map is 800 x 800 units).
        cell_size: 100 (each grid cell is 100 x 100 units).
    """
    _GLOBALS.clear()
    _GLOBALS.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "running": True,
            "tick": 0,
            "orders": [],
            "grid_size": 800,
            "cell_size": 100,
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store a value under the given global key.

    Args:
        key: Name of the global variable (e.g. ``"funds"``, ``"riders"``).
        value: Value to store.
    """
    _GLOBALS[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _GLOBALS.get(key, default)


_init()
