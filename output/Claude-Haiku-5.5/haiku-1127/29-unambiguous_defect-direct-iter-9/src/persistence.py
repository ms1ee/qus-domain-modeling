"""JSON persistence for configuration parameters and simulation state."""

import json
import logging
from typing import Any, Dict

from config import DEFAULT_PARAMS

logger = logging.getLogger("dispatch.persistence")


def load_config(path: str) -> Dict[str, int]:
    """Load system parameter overrides from a JSON file.

    The file may either contain the parameters at top level or nested under
    a ``"params"`` key. Only known, non-negative integer parameters are kept.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        Dictionary of valid overrides; empty if the file is missing or invalid.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.info("No configuration file at %s; using defaults", path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        return {}
    source = data.get("params", data)
    if not isinstance(source, dict):
        return {}

    overrides: Dict[str, int] = {}
    for key in DEFAULT_PARAMS:
        value = source.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            overrides[key] = value
    if ("speed_min" in overrides and "speed_max" in overrides
            and overrides["speed_min"] > overrides["speed_max"]):
        logger.warning("speed_min greater than speed_max; ignoring speed overrides")
        overrides.pop("speed_min")
        overrides.pop("speed_max")
    return overrides


def save_state(system, path: str) -> bool:
    """Write the current system state (funds, riders, orders) to JSON.

    Args:
        system: The active ``SystemManager``.
        path: Destination file path.

    Returns:
        True on success, False if the file could not be written.
    """
    data: Dict[str, Any] = system.to_dict()
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return True
    except OSError as exc:
        logger.error("Could not save state to %s: %s", path, exc)
        return False
