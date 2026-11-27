"""Process-wide variable store for the food delivery dispatch simulator.

Shared state (funds, riders, orders, simulated tick, ...) lives in a
module-level dictionary so that any module can read or write it without
passing objects around explicitly.

Keys used across the program:
    funds (int): system funds, may become negative.
    riders (list[Rider]): active rider objects.
    rider_id_counter (int): last issued rider id (starts at 0).
    is_running (bool): main loop control flag.
    current_tick (int): simulated time in ticks.
    orders (list[Order]): every order created in this session.
    order_history (list[Order]): completed orders in completion order.
    order_id_counter (int): last issued order id.
    max_rider_load (int): maximum concurrent orders per rider.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the store to the default values of a fresh simulation.

    Returns:
        None. The module-level dictionary is replaced in place.
    """
    global _global_dict
    _global_dict = {
        "funds": 0,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "orders": [],
        "order_history": [],
        "order_id_counter": 0,
        "max_rider_load": 3,
    }
    logger.debug("Global variable store initialised.")


def set_value(key, value) -> None:
    """Store a value under the given key.

    Args:
        key (str): Name of the global variable.
        value (Any): Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key (str): Name of the global variable.
        default (Any): Value returned when the key does not exist.

    Returns:
        Any: The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
