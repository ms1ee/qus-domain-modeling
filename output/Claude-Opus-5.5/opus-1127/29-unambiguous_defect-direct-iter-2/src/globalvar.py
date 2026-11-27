"""Global variable registry shared by every module of the dispatch simulator.

The registry is a plain dictionary hidden behind three helpers so that
all modules use the same storage. Keys used by the system:

* ``config``            - dict of system parameters
* ``funds``             - int, system funds (may become negative)
* ``riders``            - list[Rider]
* ``rider_id_counter``  - int, last issued rider id
* ``running``           - bool, main loop flag
* ``time``              - int, current simulation tick
* ``orders``            - list[Order], order history
* ``last_rider_added``  - bool, whether the last assignment recruited a rider
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
