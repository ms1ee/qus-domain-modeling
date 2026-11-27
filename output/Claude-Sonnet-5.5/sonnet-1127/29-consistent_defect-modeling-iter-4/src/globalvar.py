"""Global variable storage shared across the whole program."""
import sys

_STORE_NAME = "_food_dispatch_globals"


def _store():
    """Return the single shared dict (survives duplicate module imports)."""
    return sys.__dict__.setdefault(_STORE_NAME, {})


def _init():
    """Reset all global variables to their initial values."""
    s = _store()
    s.clear()
    s.update({
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "order_id_counter": 0,
    })


def set_value(key, value):
    """Set a global value."""
    _store()[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _store().get(key, default)
