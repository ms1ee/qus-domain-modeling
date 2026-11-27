"""Global variable storage."""

_global_dict = {}


def _init():
    """Initialise global storage."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Set a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Get a global value."""
    return _global_dict.get(key, default)
