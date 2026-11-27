"""Global variable storage for the dispatch system.

Simple key/value store shared between modules.  Typical keys:

* ``funds``             -- int, system funds (may become negative)
* ``riders``            -- list[Rider]
* ``rider_id_counter``  -- int, last issued rider id
* ``running``           -- bool, main loop control
* ``time``              -- int, simulated tick counter
* ``orders``            -- list[Order], every order ever created
* ``order_counter``     -- int, last issued order id
* ``config``            -- dict, system parameters
"""

_global_dict = None


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def _ensure():
    """Lazily initialise the store if ``_init`` was never called."""
    if _global_dict is None:
        _init()


def set_value(key, value):
    """Store ``value`` under ``key``."""
    _ensure()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` (or ``default``)."""
    _ensure()
    return _global_dict.get(key, default)


def has_key(key):
    """Return True if ``key`` is present in the store."""
    _ensure()
    return key in _global_dict
