"""JSON persistence for system state and configuration files."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def save_state(path: str, system) -> None:
    """Write the current system state to a JSON file.

    Args:
        path: Destination file path.
        system: SystemManager instance whose ``to_dict`` is serialized.

    Raises:
        OSError: If the file cannot be written.
    """
    data = system.to_dict()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("System state saved to %s", path)


def load_config(path: str) -> dict:
    """Load system parameters from a JSON configuration file.

    Missing or invalid files produce an empty configuration (with a warning)
    so that the program can still start with defaults.

    Args:
        path: Path to the configuration file.

    Returns:
        Dictionary of configuration values (empty if unavailable).
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("Configuration %s must contain a JSON object", path)
        return {}
    return data
