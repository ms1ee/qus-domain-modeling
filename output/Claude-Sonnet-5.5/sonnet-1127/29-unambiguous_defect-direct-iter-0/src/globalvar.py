"""Global variable storage."""

_global_dict = {}


def _init():
    """Reset the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Set a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Get a global value (default if missing)."""
    return _global_dict.get(key, default)
