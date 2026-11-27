"""Global variable store for the dispatch simulator.

The store is a simple module-level dictionary.  Typical keys:

* ``"riders"``            -- list[Rider]
* ``"orders"``            -- list[Order]
* ``"money"``             -- int, system funds (may be negative)
* ``"rider_id_counter"``  -- int, last issued rider id
* ``"running"``           -- bool, main loop flag
* ``"time"``              -- int, current simulated tick
* ``"config"``            -- dict, system configuration
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary to an empty state."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)
