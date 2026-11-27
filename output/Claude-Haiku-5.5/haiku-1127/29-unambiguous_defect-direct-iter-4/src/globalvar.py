"""Global variable storage shared across the dispatch simulator.

The store is a simple process-wide dictionary. Well-known keys include:

* ``"funds"``: integer system balance (may be negative).
* ``"riders"``: list of :class:`rider.Rider` objects.
* ``"rider_id_counter"``: last issued rider id.
* ``"running"``: boolean controlling the main loop.
* ``"tick"``: current simulated time.
* ``"orders"``: list of all created orders.
* ``"pending_orders"``: orders waiting for a rider.
* ``"system"``: the active :class:`system.SystemManager`.
"""

import logging

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 5000

_global_dict = {}


def _init():
    """Reset the global store to its default startup values.

    Riders list starts empty, the rider id counter is 0, the system is
    running, and the simulated clock starts at tick 0.
    """
    global _global_dict
    _global_dict = {
        "funds": INITIAL_FUNDS,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "pending_orders": [],
        "system": None,
    }
    logger.debug("Global variables initialised")


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
