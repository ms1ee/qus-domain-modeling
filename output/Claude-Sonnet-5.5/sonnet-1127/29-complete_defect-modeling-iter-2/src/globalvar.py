"""Global variable storage."""

_state = {}


def _init():
    """Reset the global storage."""
    global _state
    _state = {}


def set_value(key, value):
    """Store a value under key."""
    _state[key] = value


def get_value(key, default=None):
    """Fetch a value by key."""
    return _state.get(key, default)
