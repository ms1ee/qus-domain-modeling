"""System configuration: defaults and JSON configuration file loading."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "rider_cost": 300,
    "rider_start_x": 435,
    "rider_start_y": 385,
    "rider_speed": 10,
    "map_size": 800,
    "cell_size": 100,
    "ticks_per_command": 1,
    "max_run_ticks": 100000,
    "state_file": "dispatch_state.json",
}

_active = dict(DEFAULT_CONFIG)


def get(key, default=None):
    """Return an active configuration value."""
    return _active.get(key, DEFAULT_CONFIG.get(key, default))


def get_all():
    """Return a copy of the active configuration."""
    return dict(_active)


def set_active(cfg):
    """Replace the active configuration (missing keys fall back to defaults)."""
    global _active
    merged = dict(DEFAULT_CONFIG)
    if cfg:
        merged.update(cfg)
    _active = merged


def reset():
    """Reset the active configuration to defaults."""
    set_active(None)


def load_config(path=None):
    """Load a JSON configuration file and merge it with the defaults.

    Invalid or missing files are reported in the log and ignored.
    Returns the merged configuration dictionary.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                params = data.get("system", data)
                for key, value in params.items():
                    if key in DEFAULT_CONFIG:
                        cfg[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", path, exc)
    return cfg
