"""Global variable store shared by the dispatch system modules.

The store is a plain dictionary accessed through ``set_value`` and
``get_value`` so that modules never hold direct references to shared
mutable state. Well-known keys include:

* ``funds``: system fund balance (int, may be negative)
* ``riders``: list of Rider objects
* ``rider_id_counter``: last issued rider ID
* ``running``: main loop control flag
* ``tick``: current simulated time
* ``config``: system parameter dictionary
* ``order_history``: list of every Order created
* ``restaurants`` / ``customers``: sets of grid-centre coordinates in use
"""

_global_dict = {}


def _init():
    """Reset the global store to an empty dictionary.

    Called by ``system.init_system`` before default values are installed.
    """
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable key identifying the global value.
        value: Any object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Key to look up.
        default: Value returned when ``key`` is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)
