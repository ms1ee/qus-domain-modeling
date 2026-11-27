"""Global variable storage."""

_state = {}


def _init():
    """Reset the global store."""
    global _state
    _state = {}


def set_value(key, value):
    """Set a global value."""
    _state[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _state.get(key, default)
