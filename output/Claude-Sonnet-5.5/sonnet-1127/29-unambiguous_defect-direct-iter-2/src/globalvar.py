"""Global variable storage."""

_state = {}


def _init():
    """Reset all global values."""
    global _state
    _state = {
        "funds": 10000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
    }


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)
