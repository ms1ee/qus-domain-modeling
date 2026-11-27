"""System parameters and JSON persistence helpers.

Parameters are read from a JSON configuration file (``config.json`` by
default). Missing or invalid entries fall back to the defaults defined here.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_STATE_PATH = "dispatch_state.json"

DEFAULT_PARAMS: Dict[str, Any] = {
    "initial_funds": 300,      # starting system funds (may be negative)
    "recruit_threshold": 300,  # funds needed to recruit a new rider
    "recruit_cost": 300,       # funds spent when a rider is recruited
    "order_fee": 150,          # income credited when an order is placed
    "default_speed": 100,      # rider speed in units per tick
    "load_penalty": 200,       # assignment penalty per active order
    "fuel_divisor": 10,        # fuel cost = order distance // fuel_divisor
}

_POSITIVE_KEYS = {"recruit_threshold", "recruit_cost", "default_speed", "fuel_divisor"}
_NON_NEGATIVE_KEYS = {"order_fee", "load_penalty"}


def _is_valid(key: str, value: Any) -> bool:
    """Check that a configuration value is an integer within its allowed range.

    Args:
        key: Parameter name.
        value: Candidate value from the configuration file.

    Returns:
        True if the value is acceptable for the parameter.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    if key in _POSITIVE_KEYS:
        return value > 0
    if key in _NON_NEGATIVE_KEYS:
        return value >= 0
    return True


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load system parameters from a JSON configuration file.

    The file may either be a flat object of parameters or an object with a
    ``"parameters"`` section. Invalid or unknown entries are ignored with a
    warning, and missing entries keep their default values.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A new dictionary containing all system parameters.
    """
    params = dict(DEFAULT_PARAMS)
    if not os.path.exists(path):
        logger.info("Configuration file %s not found; using defaults", path)
        return params
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.error("Cannot read configuration %s: %s", path, exc)
        return params

    section = data.get("parameters", data) if isinstance(data, dict) else {}
    for key, value in section.items():
        if key not in DEFAULT_PARAMS:
            logger.warning("Unknown configuration key ignored: %s", key)
            continue
        if _is_valid(key, value):
            params[key] = value
        else:
            logger.warning("Invalid value %r for %s; default kept", value, key)
    return params


def write_json(path: str, data: Dict[str, Any]) -> None:
    """Write a dictionary to a JSON file.

    Args:
        path: Destination file path.
        data: JSON-serialisable dictionary.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    logger.info("State written to %s", path)
