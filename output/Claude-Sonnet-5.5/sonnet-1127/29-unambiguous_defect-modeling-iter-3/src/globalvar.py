"""Global shared state."""

_state = {}


def _init():
    """Reset all global values."""
    _state.clear()
    _state.update({
        "funds": 10000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
    })


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)
