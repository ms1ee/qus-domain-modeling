"""Global variable registry for the food delivery dispatch simulator.

The registry is a simple key/value store shared by every module.  Well-known
keys:

* ``"funds"``             -- int, system funds (may become negative)
* ``"riders"``            -- list[Rider], all riders in the system
* ``"rider_id_counter"``  -- int, last rider id handed out
* ``"running"``           -- bool, main loop flag
* ``"tick"``              -- int, current simulated time
* ``"orders"``            -- list[Order], every order ever created
* ``"order_id_counter"``  -- int, last order id handed out
"""

_global_dict = None


def _init():
    """(Re)initialise the global registry to an empty dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key`` (initialises the registry if needed)."""
    global _global_dict
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    if _global_dict is None:
        return default
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is present in the registry."""
    return _global_dict is not None and key in _global_dict
