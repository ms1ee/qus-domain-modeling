"""Global variable storage."""

_state = {}


def _init():
    """Reset the global store."""
    global _state
    _state = {}


def set_value(key, value):
    """Store a value."""
    _state[key] = value


def get_value(key, default=None):
    """Fetch a value (default if missing)."""
    return _state.get(key, default)
