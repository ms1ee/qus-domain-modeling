"""Global variable store."""

_state = {}


def _init():
    """Reset global state."""
    _state.clear()


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)
