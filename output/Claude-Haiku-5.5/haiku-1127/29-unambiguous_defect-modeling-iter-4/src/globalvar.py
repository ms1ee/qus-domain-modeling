"""Global variable store shared by the simulator modules.

The store is a simple module-level dictionary. Keys used across the program:

* ``"riders"``: list of ``Rider`` objects (dynamic, supports CRUD operations)
* ``"orders"``: list of ``Order`` objects
* ``"funds"``: system funds (int, may be negative)
* ``"rider_id_counter"``: last issued rider id (int)
* ``"is_running"``: main loop control flag (bool)
* ``"tick"``: current simulated time (int)
* ``"config"``: system configuration dictionary
"""

_global_vars = {"riders": []}


def _init():
    """Reset the global variable store to its initial, empty state.

    The ``"riders"`` key always exists after initialization so that
    callers can rely on it being a list.
    """
    global _global_vars
    _global_vars = {"riders": []}


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _global_vars[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when ``key`` is not present.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_vars.get(key, default)
