"""Configuration constants and runtime-overridable settings.

Map geometry is fixed by the PRD (800x800 units, 100-unit cells, 8x8 grid).
Business parameters live in SETTINGS and may be overridden by a JSON file.
"""

import json
import os

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE  # 8 cells per axis

SETTINGS = {
    "initial_funds": 10000,
    "recruitment_cost": 500,
    "max_riders": 12,
    "order_load_limit": 2,
    "load_penalty": 150,
    "delivery_fee": 80,
    "base_rider_speed": 40,
    "save_file": "dispatch_state.json",
    "log_file": "dispatch.log",
}

DEFAULT_CONFIG_FILE = "dispatch_config.json"


def load_config(path: str = DEFAULT_CONFIG_FILE) -> bool:
    """Load overrides for SETTINGS from a JSON file.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        True if a file was found and applied, False if it does not exist.

    Raises:
        ValueError: If the file content is not a JSON object or a value has
            the wrong type.
    """
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    for key, value in data.items():
        if key not in SETTINGS:
            continue
        expected = type(SETTINGS[key])
        if not isinstance(value, expected):
            raise ValueError(
                f"Setting '{key}' must be of type {expected.__name__}."
            )
        SETTINGS[key] = value
    return True
