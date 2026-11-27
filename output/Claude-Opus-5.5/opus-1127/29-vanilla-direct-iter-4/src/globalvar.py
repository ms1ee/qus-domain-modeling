"""Global variable storage shared by all modules of the dispatch system.

The store is a plain dictionary hidden behind small accessor functions so
that every module reads and writes shared state the same way.

Well known keys:
    funds             -- int, current system funds (may become negative)
    riders            -- list[Rider], all riders in the system
    rider_id_counter  -- int, last rider id handed out
    running           -- bool, controls the main loop
    time              -- int, current simulated tick
    orders            -- list[Order], every order ever created
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary to an empty state."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` when missing."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True when ``key`` is present in the store."""
    return key in _global_dict


def all_values():
    """Return a shallow copy of the whole store (for debugging)."""
    return dict(_global_dict)
