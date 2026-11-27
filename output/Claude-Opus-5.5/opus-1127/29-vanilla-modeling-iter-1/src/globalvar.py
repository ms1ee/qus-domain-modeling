"""Global variable storage for the food delivery dispatch simulator.

Provides a tiny key/value store shared between modules.  Common keys:

* ``"funds"``             -- int, system funds (may become negative)
* ``"riders"``            -- list[Rider]
* ``"rider_id_counter"``  -- int, last issued rider id
* ``"running"``           -- bool, main loop flag
* ``"tick"``              -- int, current simulated time
* ``"orders"``            -- list[Order], all orders ever created
* ``"config"``            -- Configuration instance
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary, discarding previous content."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)


def has_value(key):
    """Return True when ``key`` has been set."""
    return key in _global_dict
