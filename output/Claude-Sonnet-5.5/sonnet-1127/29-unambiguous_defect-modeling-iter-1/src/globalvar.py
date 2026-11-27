"""Global variable store."""

_globals = {}


def _init():
    """Reset the global store."""
    global _globals
    _globals = {}


def set_value(key, value):
    """Set a global value."""
    _globals[key] = value


def get_value(key, default=None):
    """Get a global value (default if missing)."""
    return _globals.get(key, default)
