"""Global variable storage."""
_state = {}


def _init():
    """Reset all global variables to their initial values."""
    global _state
    _state = {
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "funds": 0,
        "tick": 0,
        "orders": [],
        "history": [],
    }


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
