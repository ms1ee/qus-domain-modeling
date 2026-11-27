"""Global variable store shared by all simulator modules.

The store is a plain dictionary keyed by string names. ``_init()`` resets the
store to its default values. It is also executed when this module is first
imported, so ``get_value`` is always usable even before ``system.init_system``
is called.
"""

import logging
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "rider_speed": 10,
    "rider_start": [435, 385],
}

_global_dict = {}


def _init() -> None:
    """Reset the global store to its default values.

    Keys created:
        funds: System funds (int, may become negative through operating costs).
        riders: List of Rider objects.
        rider_id_counter: Last issued rider ID.
        is_running: Main loop control flag.
        current_tick: Simulated time in ticks.
        orders: Full order history (list of Order objects).
        pending_orders: Orders waiting for a rider.
        order_id_counter: Last issued order ID.
        config: System parameters (copy of DEFAULT_CONFIG).
    """
    global _global_dict
    _global_dict = {
        "funds": DEFAULT_CONFIG["initial_funds"],
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "orders": [],
        "pending_orders": [],
        "order_id_counter": 0,
        "config": deepcopy(DEFAULT_CONFIG),
    }
    logger.debug("Global variables initialised")


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
        The stored value or ``default``.
    """
    return _global_dict.get(key, default)


def next_value(key: str) -> int:
    """Increment an integer counter and return the new value.

    Args:
        key: Name of the counter variable.

    Returns:
        The incremented counter value (starting at 1).
    """
    value = int(_global_dict.get(key, 0)) + 1
    _global_dict[key] = value
    return value


_init()
