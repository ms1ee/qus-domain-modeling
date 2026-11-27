"""Global variable store for the food delivery dispatch simulator.

Keys used by the system include:

* ``"funds"``: int, system funds (may become negative)
* ``"riders"``: list[Rider], every rider in the system
* ``"rider_id_counter"``: int, last rider id handed out
* ``"order_id_counter"``: int, last order id handed out
* ``"orders"``: list[Order], every order ever created
* ``"running"``: bool, controls the main loop
* ``"time"``: int, simulated time in ticks
* ``"config"``: dict, system parameters
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary, discarding all values."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if absent."""
    return _global_dict.get(key, default)
