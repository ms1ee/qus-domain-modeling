"""Global variable store."""

_state = {}


def _init():
    """Reset all global variables to their defaults."""
    global _state
    _state = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "order_id_counter": 0,
    }


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)


_init()
