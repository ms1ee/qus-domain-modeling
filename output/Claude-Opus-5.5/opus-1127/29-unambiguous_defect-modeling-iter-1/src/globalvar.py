"""Global variable registry for the food delivery dispatch simulator.

The registry is a simple key/value store shared between modules.  Important
keys used by the system:

* ``"funds"``            - int, current system funds (may be negative)
* ``"riders"``           - list[Rider], all riders known to the system
* ``"rider_id_counter"`` - int, last rider id handed out
* ``"running"``          - bool, main-loop control flag
* ``"tick"``             - int, current simulated time
* ``"orders"``           - list[Order], full order history
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global registry."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key`` in the global registry."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (``default`` if missing)."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` exists in the registry."""
    return key in _global_dict


def keys():
    """Return a list of all registered keys."""
    return list(_global_dict.keys())
