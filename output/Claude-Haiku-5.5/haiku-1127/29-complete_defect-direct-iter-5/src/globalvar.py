"""Process-wide global variable store for the dispatch simulator.

The store is a simple module-level dictionary. Values are accessed through
``set_value`` and ``get_value`` so that every module shares the same state
(funds, rider list, rider ID counter, running flag, simulated tick, and so on).
"""

import logging
from typing import Any, Dict

from config import DEFAULT_PARAMS

logger = logging.getLogger(__name__)

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global variable table to its startup defaults.

    Defaults:
        riders: empty rider list (key "riders").
        rider_id_counter: 0, so the first rider receives ID 1.
        funds: initial system funds taken from the parameters.
        running: True, controls the main loop.
        tick: 0, the simulated time counter.
        params: system parameters copied from ``DEFAULT_PARAMS``.
        orders: history of every order created.
        pending_orders: orders waiting for a rider.
    """
    _global_dict.clear()
    _global_dict.update(
        {
            "riders": [],
            "rider_id_counter": 0,
            "funds": DEFAULT_PARAMS["initial_funds"],
            "running": True,
            "tick": 0,
            "params": dict(DEFAULT_PARAMS),
            "orders": [],
            "pending_orders": [],
        }
    )
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
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
