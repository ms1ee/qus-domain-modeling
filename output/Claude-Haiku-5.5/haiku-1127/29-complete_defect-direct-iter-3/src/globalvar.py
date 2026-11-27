"""Global variable store shared by all simulator modules.

Values live in a module-level dictionary. ``_init`` resets the store to its
default layout, and ``set_value`` / ``get_value`` read and write individual keys.
Well-known keys include:

* ``"riders"``: list of Rider objects (dynamic, supports CRUD).
* ``"rider_id_counter"``: integer counter used to create unique rider IDs.
* ``"running"``: boolean controlling the main loop.
* ``"funds"``: integer system funds (may be negative).
* ``"tick"``: current simulated time (one unit per tick).
* ``"orders"``: list of every Order created in this session.
"""

_global_dict = {}


def _init():
    """Reset the global variable store to its default state.

    The defaults correspond to the PRD initialization rules: an empty rider
    list, rider ID counter 0, running state True, and simulated time 0.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "funds": 0,
        "tick": 0,
        "orders": [],
    }


def set_value(key, value):
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: Hashable identifier of the variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Identifier of the variable.
        default: Value returned when ``key`` is not present.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
