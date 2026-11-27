"""Process-wide global variable store.

Holds the shared runtime state of the dispatch simulator: system funds, the
rider list, ID counters, the running flag, the simulated clock, and the order
history. Other modules read and write values through ``get_value`` and
``set_value`` instead of importing each other's state directly.
"""

import logging

logger = logging.getLogger(__name__)

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    Creates the default keys used by the system: funds, riders, rider ID
    counter, running flag, simulated tick, order list, order counter, and
    configuration.
    """
    global _global_dict
    _global_dict = {
        "funds": 0,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "order_counter": 0,
        "config": None,
    }
    logger.debug("Global variable store initialised")


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: The name of the global variable (for example ``"riders"``).
        value: The value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under the given key.

    Args:
        key: The name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
