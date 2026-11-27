"""Global variable storage for the food delivery dispatch simulator.

The simulator keeps its shared runtime state (funds, riders, orders, the
simulated clock, ...) in a single module-level dictionary.  Access it with
:func:`set_value` and :func:`get_value`.

Well-known keys:

* ``"funds"``              -- int, system funds (may be negative)
* ``"riders"``             -- list[Rider]
* ``"rider_id_counter"``   -- int, last rider id handed out
* ``"running"``            -- bool, main loop flag
* ``"tick"``               -- int, current simulated time
* ``"orders"``             -- list[Order], order history
* ``"order_id_counter"``   -- int, last order id handed out
* ``"recruitment_cost"``   -- int, cost of recruiting one rider
* ``"max_riders"``         -- int, maximum number of riders
* ``"rider_speed"``        -- int, default rider speed (units/tick)
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary, discarding all stored values."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)


def has_value(key):
    """Return True if ``key`` has been set."""
    return key in _global_dict


def all_values():
    """Return a shallow copy of the whole global dictionary."""
    return dict(_global_dict)
