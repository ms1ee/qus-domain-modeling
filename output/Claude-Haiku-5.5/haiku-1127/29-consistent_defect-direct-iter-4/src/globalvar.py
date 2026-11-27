"""Process-wide key/value store used as the simulator's global state.

Keys used by the simulator:
    "riders"            list[Rider] - all riders currently in the system
    "orders"            list[Order] - every order created in this session
    "funds"             int         - system funds (may be negative)
    "rider_id_counter"  int         - last issued rider id
    "running"           bool        - main loop control flag
    "tick"              int         - current simulated time
    "grid_map"          list        - 8x8 grid of cell top-left corners
"""

import logging

logger = logging.getLogger(__name__)

_store = {"riders": []}


def _init():
    """Reset the global store to its default empty state.

    Returns:
        None
    """
    global _store
    _store = {"riders": []}
    logger.debug("Global variable store initialised.")


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable identifier, e.g. ``"riders"``.
        value: Any object to store.

    Returns:
        None
    """
    _store[key] = value


def get_value(key):
    """Return the value stored under ``key``.

    Args:
        key: Identifier used with :func:`set_value`.

    Returns:
        The stored value, or ``None`` when the key is absent.
    """
    return _store.get(key)
