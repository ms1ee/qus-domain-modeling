"""Global variable registry shared by all modules of the dispatch simulator.

The registry is a simple module-level dictionary.  ``_init`` resets it,
``set_value`` / ``get_value`` write and read individual keys.

Well known keys:
    funds               int, system funds (may be negative)
    riders              list[Rider]
    rider_id_counter    int, last rider id handed out
    running             bool, main loop flag
    time                int, current simulated tick
    orders              list[Order], every order ever created
    pending_orders      list[Order], orders still waiting for a rider
    order_id_counter    int, last order id handed out
    config              dict, active configuration
"""

_global_dict = {}


def _init():
    """Reset the global registry to an empty dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key`` in the global registry."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default`` if missing)."""
    return _global_dict.get(key, default)


def has_value(key):
    """Return True if ``key`` exists in the global registry."""
    return key in _global_dict
