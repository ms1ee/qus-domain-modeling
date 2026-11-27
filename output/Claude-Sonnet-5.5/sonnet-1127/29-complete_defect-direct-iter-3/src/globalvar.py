"""Global variable storage."""

_state = {}


def _init():
    """Reset all global values to their defaults."""
    global _state
    _state = {
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "funds": 0,
        "time": 0,
        "orders": [],
    }


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)


_init()
