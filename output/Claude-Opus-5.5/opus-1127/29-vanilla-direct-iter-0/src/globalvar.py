"""Global variable storage shared by all modules of the dispatch simulator.

Keys used by the system:
    funds              -- int, system funds (may be negative)
    riders             -- list[Rider]
    rider_id_counter   -- int, last issued rider id
    running            -- bool, main loop control flag
    orders             -- list[Order], every order ever created
    pending_orders     -- list[Order], orders not yet assigned to a rider
    time               -- int, current simulation tick
    order_id_counter   -- int, last issued order id
"""

_global_dict = {}


def _init():
    """Reset the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    return _global_dict.get(key, default)
