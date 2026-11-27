"""System configuration parameters for the food delivery dispatch simulator.

All tunable parameters live in the module-level ``SETTINGS`` dictionary.
They can be overridden at start-up with a JSON configuration file through
:func:`load_config_file`.
"""

import json
import logging

logger = logging.getLogger(__name__)

SETTINGS = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_funds_threshold": 300,
    "rider_start_x": 435,
    "rider_start_y": 385,
    "rider_speed": 10,
    "map_size": 800,
    "cell_size": 100,
    "grid_dim": 8,
    "state_file": "delivery_state.json",
}


def load_config_file(path):
    """Load parameter overrides from a JSON file into ``SETTINGS``.

    Args:
        path: Path to a JSON file containing a single object whose keys are
            parameter names from ``SETTINGS``.

    Returns:
        dict: A copy of the effective settings after applying the overrides.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or a value has the wrong type.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    for key, value in data.items():
        if key not in SETTINGS:
            logger.warning("Ignoring unknown configuration key %r", key)
            continue
        expected_type = type(SETTINGS[key])
        if not isinstance(value, expected_type) or isinstance(value, bool):
            raise ValueError(
                f"Configuration key {key!r} must be of type "
                f"{expected_type.__name__}."
            )
        SETTINGS[key] = value
    return dict(SETTINGS)
