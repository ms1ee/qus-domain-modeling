"""Global variable store for the dispatch system."""

_state = {}


def _init():
    """Reset all global values to their defaults."""
    _state.clear()
    _state["funds"] = 1000
    _state["riders"] = []
    _state["rider_id_counter"] = 0
    _state["running"] = True
    _state["time"] = 0
    _state["orders"] = []
    _state["history"] = []


def set_value(key, value):
    """Set a global value."""
    if not _state:
        _init()
    _state[key] = value


def get_value(key, default=None):
    """Get a global value (None/default if missing)."""
    if not _state:
        _init()
    return _state.get(key, default)
