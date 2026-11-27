"""Global variable store shared by all modules of the dispatch simulator.

Usage::

    import globalvar
    globalvar._init()
    globalvar.set_value("riders", [])
    riders = globalvar.get_value("riders")

Well-known keys:

* ``riders``            -- list[Rider]
* ``funds``             -- int, system funds (may become negative)
* ``rider_id_counter``  -- int, last issued rider id
* ``running``           -- bool, main loop control flag
* ``tick``              -- int, current simulated time
* ``orders``            -- list[Order], every order created in this session
* ``order_history``     -- list[dict], archived orders loaded from disk
* ``config``            -- dict, active configuration parameters
"""

_global_dict = {}


def _init():
    """(Re)initialise the global dictionary, discarding all stored values."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default`` if missing)."""
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is present in the store."""
    return key in _global_dict
