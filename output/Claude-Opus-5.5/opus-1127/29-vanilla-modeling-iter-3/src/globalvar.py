"""Global variable registry shared by all modules of the dispatch simulator.

Keys used by the application:

* ``funds`` (int) - system funds (may become negative).
* ``riders`` (list[Rider]) - all riders in the system.
* ``rider_id_counter`` (int) - last rider ID that was issued.
* ``running`` (bool) - main loop flag.
* ``tick`` (int) - current simulated time.
* ``orders`` (list[Order]) - every order created so far.
* ``order_id_counter`` (int) - last order ID that was issued.
* ``recruitment_cost`` (int) - cost of recruiting one rider.
* ``rider_speed`` (int) - speed for newly recruited riders.
* ``last_recruited`` (bool) - whether the last assignment recruited a rider.
"""

_global_dict = None


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def is_initialized():
    """Return True if :func:`_init` has been called."""
    return _global_dict is not None


def set_value(key, value):
    """Store ``value`` under ``key``; lazily initialises the registry."""
    if _global_dict is None:
        _init()
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key`` or ``default`` if missing."""
    if _global_dict is None:
        return default
    return _global_dict.get(key, default)
