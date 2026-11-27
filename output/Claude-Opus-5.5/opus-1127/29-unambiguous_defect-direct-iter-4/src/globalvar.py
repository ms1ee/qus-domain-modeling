"""Global variable management for the dispatch simulator.

The module keeps a single dictionary that stores the shared system state
(funds, riders, rider id counter, running flag, simulated time, orders...).
"""

_global_dict = {}


def _init():
    """(Re)initialise the global variable dictionary."""
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
