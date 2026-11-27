"""Process-wide shared variable store.

Holds the global system state: funds, the rider list, ID counters, the
running flag, the simulated clock and the order lists.
"""

import logging

logger = logging.getLogger(__name__)

_store = {}


def _init():
    """Reset the global store to its startup defaults.

    Rider list starts empty, rider ID counter is 0, the system is running,
    funds are 0 and the simulated tick is 0.
    """
    global _store
    _store = {
        "riders": [],
        "rider_id_counter": 0,
        "funds": 0,
        "running": True,
        "tick": 0,
        "order_id_counter": 0,
        "orders": [],
        "pending_orders": [],
    }
    logger.debug("Global variable store initialised")


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Name of the global variable, e.g. ``"riders"``.
        value: Value to store.
    """
    _store[key] = value


def get_value(key):
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.

    Returns:
        The stored value, or None if the key does not exist.
    """
    return _store.get(key)


_init()
