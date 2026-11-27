"""Process-wide key/value store acting as the system's global variable table.

Keys used by the program:
    funds, riders, rider_id_counter, running, tick, config, order_manager
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_global_dict: Dict[str, Any] = {}


def _init():
    """Reset the global variable table to its default values.

    Sets system funds to 1000, an empty rider list, rider ID counter to 0,
    the running flag to True and the simulated tick to 0.
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
    }
    logger.debug("Global variables initialised")


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable (e.g. ``"riders"``).
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
