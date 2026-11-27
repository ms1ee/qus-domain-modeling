"""Global variable registry shared by all modules of the dispatch system.

The registry is a plain dictionary hidden behind ``set_value``/``get_value``.
Well-known keys:

* ``"riders"``            -- list[Rider]
* ``"orders"``            -- list[Order] (order history)
* ``"funds"``             -- int, system funds (may be negative)
* ``"rider_id_counter"``  -- int, last rider id handed out
* ``"order_id_counter"``  -- int, last order id handed out
* ``"running"``           -- bool, main loop flag
* ``"time"``              -- int, current simulated tick
"""

_global_dict = None


def _init():
    """(Re)initialise the global registry to an empty dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    """Lazily initialise the registry if ``_init`` was never called."""
    if _global_dict is None:
        _init()


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (``default`` if missing)."""
    _ensure()
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is present in the registry."""
    _ensure()
    return key in _global_dict
