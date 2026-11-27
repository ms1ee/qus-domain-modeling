"""Configuration loading and JSON state persistence."""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 300,
    "hire_threshold": 300,
    "hire_cost": 300,
    "rider_speed": 50,
    "base_delivery_fee": 100,
    "distance_fee_divisor": 10,
}


def load_config(path: Optional[str] = None) -> Dict[str, int]:
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Optional path to a JSON object of parameter overrides.
            ``None`` returns the defaults only.

    Returns:
        A dictionary with every known configuration key.

    Raises:
        FileNotFoundError: If an explicit path does not exist.
        ValueError: If the file content is malformed or has invalid values.
    """
    config = dict(DEFAULT_CONFIG)
    if path is None:
        return config
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a JSON object")
    for key, value in data.items():
        if key not in DEFAULT_CONFIG:
            logger.warning("Ignoring unknown configuration key %r", key)
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Configuration value for {key!r} must be an integer")
        config[key] = value
    if config["rider_speed"] <= 0 or config["distance_fee_divisor"] <= 0:
        raise ValueError("rider_speed and distance_fee_divisor must be positive")
    return config


def save_state(path: str, snapshot: Dict[str, Any]) -> None:
    """Write a snapshot of the system state to a JSON file atomically.

    Args:
        path: Destination file path.
        snapshot: JSON-serialisable dictionary describing the state.
    """
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
    os.replace(temp_path, path)
    logger.info("State saved to %s", path)
