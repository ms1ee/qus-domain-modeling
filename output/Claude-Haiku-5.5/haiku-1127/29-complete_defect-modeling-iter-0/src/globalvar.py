"""Process-wide key/value store used to share system state between modules.

The store is a plain dictionary. Call ``_init()`` to reset it to defaults.
Keys used by the system:

* ``funds`` (int): system fund balance, may be negative.
* ``rider_id_counter`` (int): last issued rider ID.
* ``is_running`` (bool): controls the main execution loop.
* ``current_tick`` (int): simulated time, advanced once per tick.
* ``riders`` (list[Rider]): dynamic list of active riders.
* ``config`` (dict): system parameters loaded from the JSON configuration.
* ``grid`` (Grid): the 8x8 city grid.
* ``order_manager`` (OrderManager): owner of all orders.
* ``order_id_counter`` (int): last issued order ID.
"""

_global_dict = {}


def _init():
    """Reset the global store to its default values.

    Every core key is initialised here so that other modules can rely on
    the keys existing.
    """
    global _global_dict
    _global_dict = {
        "funds": 0,
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "riders": [],
        "config": {},
        "grid": None,
        "order_manager": None,
    }


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable identifier of the global value.
        value: The value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Identifier of the global value.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
