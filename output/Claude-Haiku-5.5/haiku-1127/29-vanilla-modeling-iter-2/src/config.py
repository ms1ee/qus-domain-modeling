"""Configuration loading and JSON state persistence.

System parameters can be customised through a JSON file. Simulation state
(system parameters, rider information and order history) can be saved to a
JSON file at any time.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_threshold": 300,
    "rider_speed": 10,
}


def load_config(path: str) -> Dict[str, int]:
    """Load system parameters from a JSON file.

    The file may either be a flat object of parameter names and integer
    values, or contain such an object under the ``system_parameters`` key.
    Unknown keys are ignored. On any error the defaults are returned.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A dictionary with every known system parameter.
    """
    settings: Dict[str, int] = dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read configuration %s: %s", path, exc)
        return settings

    if not isinstance(data, dict):
        logger.error("Configuration %s must contain a JSON object", path)
        return settings

    params = data.get("system_parameters", data)
    if not isinstance(params, dict):
        logger.error("'system_parameters' in %s must be an object", path)
        return settings

    for key in DEFAULT_CONFIG:
        if key in params:
            try:
                settings[key] = int(params[key])
            except (TypeError, ValueError):
                logger.warning("Invalid value for %s in %s; using default", key, path)
    return settings


def save_state(path: str, system: Any, order_manager: Any) -> None:
    """Persist the current simulation state to a JSON file.

    The file is written atomically through a temporary file.

    Args:
        path: Destination file path.
        system: ``SystemManager`` instance providing ``snapshot()``.
        order_manager: ``OrderManager`` instance providing ``to_dicts()``.
    """
    payload = {
        "system_parameters": {
            "initial_funds": system.initial_funds,
            "recruit_cost": system.recruit_cost,
            "recruit_threshold": system.recruit_threshold,
            "rider_speed": system.rider_speed,
        },
        "system_state": system.snapshot(),
        "order_history": order_manager.to_dicts(),
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp_path, path)
    logger.info("State saved to %s", path)
