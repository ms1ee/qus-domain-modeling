"""Global variable storage shared across the dispatch system modules.

The store is a simple module-level dictionary. Keys used by the system:

* ``funds`` (int): system fund balance (may become negative).
* ``riders`` (list[Rider]): all riders.
* ``rider_id_counter`` (int): auto-incrementing rider id counter.
* ``running`` (bool): main loop flag.
* ``time`` (int): simulated time in ticks.
* ``orders`` (list[Order]): order history.
* ``pending_orders`` (list[Order]): orders waiting for a rider.
* ``order_counter`` (int): auto-incrementing order id counter.
* ``config`` (dict): system configuration.
"""

_global_dict = None


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``.

    :param key: name of the global variable.
    :param value: value to store.
    """
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if absent.

    :param key: name of the global variable.
    :param default: value returned when the key is missing.
    """
    if _global_dict is None:
        _init()
    return _global_dict.get(key, default)


def current_time():
    """Return the current simulated time (ticks), 0 if unset."""
    value = get_value("time")
    return value if isinstance(value, int) else 0
