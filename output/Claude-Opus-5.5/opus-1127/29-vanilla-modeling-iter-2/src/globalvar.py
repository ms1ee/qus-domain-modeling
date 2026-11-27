"""Global variable store shared by all modules of the dispatch simulator.

Keys used by the system:
    funds              int   - system funds (may be negative)
    riders             list  - list of Rider objects
    rider_id_counter   int   - last issued rider id
    running            bool  - main loop flag
    current_tick       int   - simulated time
    orders             list  - every Order ever created
    order_id_counter   int   - last issued order id
    recruitment_cost   int
    rider_speed        int
    rider_start        tuple
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is defined."""
    return key in _global_dict


def snapshot():
    """Return a shallow copy of the global dictionary."""
    return dict(_global_dict)
