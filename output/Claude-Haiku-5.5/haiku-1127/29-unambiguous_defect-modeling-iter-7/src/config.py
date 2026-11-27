"""JSON configuration and state persistence."""

import json
import logging
import os
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)

DEFAULT_PARAMETERS: Dict[str, int] = {
    "initial_funds": 5000,
    "rider_recruitment_cost": 500,
    "max_riders": 20,
    "rider_speed": 20,
}


class SystemConfig:
    """Loads system parameters from and saves state to a JSON file.

    Attributes:
        config_file_path: Path of the JSON configuration file.
        parameters: Effective system parameters.
        saved_state: State dictionary read from the file, if any.
    """

    def __init__(self, config_file_path: str = "config.json") -> None:
        """Create a configuration holder with default parameters.

        Args:
            config_file_path: Location of the JSON file.
        """
        self.config_file_path = config_file_path
        self.parameters: Dict[str, Any] = dict(DEFAULT_PARAMETERS)
        self.saved_state: Optional[dict] = None

    def load(self) -> Dict[str, Any]:
        """Load parameters from the configuration file when it exists.

        Invalid or unreadable files are logged and the defaults are kept.

        Returns:
            Dict[str, Any]: Effective parameters.
        """
        if not os.path.exists(self.config_file_path):
            LOGGER.info("No configuration file at %s; using defaults", self.config_file_path)
            return dict(self.parameters)
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.error("Could not read configuration: %s", exc)
            return dict(self.parameters)
        if not isinstance(data, dict):
            LOGGER.error("Configuration root must be an object; using defaults")
            return dict(self.parameters)
        params = data.get("parameters", data)
        if isinstance(params, dict):
            for key, default in DEFAULT_PARAMETERS.items():
                value = params.get(key, default)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    self.parameters[key] = value
                else:
                    LOGGER.warning("Invalid value for %s; using %s", key, default)
        state = data.get("state")
        self.saved_state = state if isinstance(state, dict) else None
        return dict(self.parameters)

    def save(self, state: dict) -> str:
        """Write parameters and a state snapshot to the configuration file.

        Args:
            state: JSON-compatible snapshot of the simulation.

        Returns:
            str: Path of the written file.

        Raises:
            OSError: If the file cannot be written.
        """
        payload = {"parameters": self.parameters, "state": state}
        tmp_path = self.config_file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp_path, self.config_file_path)
        return self.config_file_path
