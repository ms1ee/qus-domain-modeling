"""Global variable store shared by all dispatch modules.

Keys used by the system:
    funds (int)               -- system fund balance, may be negative
    riders (list[Rider])      -- dynamic rider roster
    rider_id_counter (int)    -- auto-incrementing rider id source
    running (bool)            -- main loop control flag
    time (int)                -- simulation tick counter
    orders (list[Order])      -- full order history
    pending_orders (list[Order]) -- orders waiting for a rider
    rider_speed, recruit_min_funds, recruit_cost -- tunable parameters
"""

import logging

_store = {}

logger = logging.getLogger("dispatch.globalvar")


def _init():
    """Reset every global variable to its startup default value."""
    _store.clear()
    _store.update({
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
        "pending_orders": [],
        "rider_speed": 20,
        "recruit_min_funds": 300,
        "recruit_cost": 500,
    })
    logger.debug("Global variables initialised")


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default``.
    """
    return _store.get(key, default)


_init()
