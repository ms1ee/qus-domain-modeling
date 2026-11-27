"""Global state storage."""

_state = {}


def _init():
    """Reset all global variables to initial values."""
    _state.clear()
    _state.update({
        "funds": 10000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
    })


def set_value(key, value):
    """Set a global value."""
    if not _state:
        _init()
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    if not _state:
        _init()
    return _state.get(key, default)
