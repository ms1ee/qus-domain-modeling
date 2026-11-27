"""Global variable store shared across the dispatch simulator modules.

The store is a simple module-level dictionary. ``_init()`` resets it to the
default values defined in the PRD, and ``set_value`` / ``get_value`` provide
access by key. The key ``"riders"`` holds the list of ``Rider`` objects.
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global variable store with default values.

    Default values:
        funds: 1000 (system operating funds)
        riders: empty list of Rider objects
        rider_id_counter: 0 (last issued rider ID)
        is_running: True (main loop control flag)
        current_tick: 0 (simulated time)
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "config": {},
    }


def set_value(key, value):
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
