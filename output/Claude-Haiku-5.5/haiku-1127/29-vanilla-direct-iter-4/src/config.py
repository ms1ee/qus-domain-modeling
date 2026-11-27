"""System configuration parameters and JSON persistence helpers."""

import json
import logging
import os

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "config.json"
)

# Tunable system parameters. Only keys listed here may be overridden by a
# configuration file.
PARAMS = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_min_funds": 300,
    "rider_speed": 10,
    "spawn_x": 435,
    "spawn_y": 385,
    "max_run_ticks": 10000,
}


def load_config(path=CONFIG_PATH):
    """Load system parameters from a JSON configuration file.

    The file may either be a flat object or contain a ``"params"`` object.
    Unknown keys and invalid values are ignored with a warning. A missing or
    unreadable file leaves the defaults in place.

    Args:
        path: Location of the JSON configuration file.

    Returns:
        A copy of the effective parameter dictionary.
    """
    if not os.path.exists(path):
        logger.info("No configuration file at %s; using defaults.", path)
        return dict(PARAMS)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return dict(PARAMS)

    if not isinstance(data, dict):
        logger.warning("Configuration %s must contain a JSON object.", path)
        return dict(PARAMS)

    values = data.get("params", data)
    if not isinstance(values, dict):
        return dict(PARAMS)

    for key, value in values.items():
        if key not in PARAMS:
            logger.warning("Ignoring unknown configuration key '%s'.", key)
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            logger.warning("Ignoring invalid value %r for '%s'.", value, key)
            continue
        PARAMS[key] = value
    return dict(PARAMS)


def write_json(path, data):
    """Write a dictionary to a JSON file.

    Args:
        path: Destination file path.
        data: JSON-serialisable dictionary.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
