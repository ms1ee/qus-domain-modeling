"""Global variable registry for the food delivery dispatch simulator.

Keys used by the system:

* ``funds``             - int, system fund balance (may be negative)
* ``riders``            - list[Rider]
* ``rider_id_counter``  - int, last issued rider id
* ``running``           - bool, controls the main loop
* ``time``              - int, current simulated tick
* ``orders``            - list[Order], every order ever created
* ``order_id_counter``  - int, last issued order id
* ``rider_speed``       - int, default rider speed (units/tick)
* ``config``            - dict, active configuration
"""

_global_dict = {}


def _init():
    """Reset the global registry to an empty state."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default`` if missing)."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` has been set."""
    return key in _global_dict
