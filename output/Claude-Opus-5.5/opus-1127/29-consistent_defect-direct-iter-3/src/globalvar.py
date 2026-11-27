"""Global variable storage for the food delivery dispatch simulator.

The simulator keeps its shared state (funds, riders, orders, simulated
time, ...) in a single module-level dictionary so that every module can
access it without passing references around.

Well known keys:

* ``"funds"``            -- int, system funds (may become negative)
* ``"riders"``           -- list[Rider], all riders in the system
* ``"rider_id_counter"`` -- int, last rider id handed out
* ``"running"``          -- bool, main loop flag
* ``"current_time"``     -- int, simulated time in ticks
* ``"orders"``           -- list[Order], every order ever created
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary, discarding all values."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key`` in the global dictionary."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if absent."""
    return _global_dict.get(key, default)


def has_value(key):
    """Return True when ``key`` is present in the global dictionary."""
    return key in _global_dict
