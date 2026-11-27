"""Configuration loading for the food delivery dispatch simulator.

System parameters are read from an optional JSON file. Missing or invalid
entries fall back to the built-in defaults so the program always starts.
"""

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("dispatch.config")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
DEFAULT_STATE_PATH = os.path.join(PROJECT_ROOT, "dispatch_state.json")


@dataclass
class Configuration:
    """System parameters for the dispatch simulator.

    Attributes:
        initial_funds: Starting balance of the system (may go negative later).
        default_rider_speed: Base rider speed in units per tick.
        recruitment_cost: Funds deducted when a new rider is recruited.
        delivery_fee: Funds credited for each completed order.
        rider_upkeep: Funds deducted per tick for each busy rider.
        max_riders: Upper limit on the number of riders.
        max_orders_per_rider: Maximum active orders a single rider may hold.
        save_on_exit: Whether to save the state file when the program exits.
        state_file_path: JSON file used to persist the system state.
        log_level: Logging level name (e.g. "WARNING", "DEBUG").
        config_file_path: Path of the configuration file that was read.
    """

    initial_funds: int = 5000
    default_rider_speed: int = 50
    recruitment_cost: int = 300
    delivery_fee: int = 150
    rider_upkeep: int = 1
    max_riders: int = 20
    max_orders_per_rider: int = 3
    save_on_exit: bool = True
    state_file_path: str = DEFAULT_STATE_PATH
    log_level: str = "WARNING"
    config_file_path: str = DEFAULT_CONFIG_PATH

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Configuration":
        """Load configuration from a JSON file, using defaults as fallback.

        Args:
            path: Optional path to the JSON configuration file.

        Returns:
            A Configuration instance with values from the file applied.
        """
        config_path = path or DEFAULT_CONFIG_PATH
        cfg = cls(config_file_path=config_path)
        if not os.path.exists(config_path):
            return cfg
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not read configuration %s (%s); using defaults.",
                config_path, exc,
            )
            return cfg
        if not isinstance(data, dict):
            logger.warning("Configuration root must be an object; using defaults.")
            return cfg
        for fld in dataclasses.fields(cls):
            if fld.name == "config_file_path" or fld.name not in data:
                continue
            value = data[fld.name]
            current = getattr(cfg, fld.name)
            is_bool_mismatch = isinstance(current, int) and isinstance(value, bool)
            if isinstance(value, type(current)) and not is_bool_mismatch:
                setattr(cfg, fld.name, value)
            else:
                logger.warning("Ignoring invalid value for '%s'.", fld.name)
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a plain dictionary.

        Returns:
            Dictionary of configuration names to values.
        """
        return dataclasses.asdict(self)
