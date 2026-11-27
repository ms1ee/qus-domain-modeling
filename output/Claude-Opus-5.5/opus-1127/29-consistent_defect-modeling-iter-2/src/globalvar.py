"""Global variable store shared across modules.

Holds the core system data (funds, riders, rider ID counter, running state,
simulated tick, orders, ...). Keys used by the program:

- ``funds`` (int, may be negative)
- ``riders`` (list[Rider])
- ``rider_id`` (int, rider ID counter)
- ``running`` (bool)
- ``tick`` (int, simulated time)
- ``orders`` (list[Order])
- ``order_id_counter`` (int)
- ``recruitment_cost`` / ``recruitment_threshold`` / ``rider_speed`` (int)
"""

_global_dict = None


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default``)."""
    if _global_dict is None:
        _init()
    return _global_dict.get(key, default)
