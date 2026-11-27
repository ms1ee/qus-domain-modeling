"""System configuration loaded from a JSON file with sane defaults."""

import json
import logging
import os
from dataclasses import asdict, dataclass, fields

from grid import LATTICE_STEP

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "dispatch_config.json"


@dataclass
class SystemConfig:
    """Tunable parameters of the dispatch simulation.

    Attributes:
        recruitment_threshold: Funds level at which a new rider is recruited.
        recruitment_cost: Funds spent when a rider is recruited.
        default_rider_speed: Movement speed in units per tick. Must divide 50
            so that riders always stay on the routing lattice.
        map_size: Map width/height in units.
        cell_size: Grid cell width/height in units.
        order_fee: Funds income earned for each accepted order.
        initial_funds: Funds available when the system starts.
        config_file_path: Path the configuration was loaded from.
    """

    recruitment_threshold: int = 300
    recruitment_cost: int = 300
    default_rider_speed: int = 50
    map_size: int = 800
    cell_size: int = 100
    order_fee: int = 100
    initial_funds: int = 300
    config_file_path: str = DEFAULT_CONFIG_PATH

    def validate(self) -> None:
        """Check parameter consistency.

        Raises:
            ValueError: If any parameter is invalid.
        """
        positive = ("recruitment_threshold", "recruitment_cost",
                    "default_rider_speed", "map_size", "cell_size", "order_fee")
        for name in positive:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if isinstance(self.initial_funds, bool) or not isinstance(self.initial_funds, int):
            raise ValueError("initial_funds must be an integer")
        if self.map_size % self.cell_size != 0:
            raise ValueError("map_size must be a multiple of cell_size")
        if LATTICE_STEP % self.default_rider_speed != 0:
            raise ValueError(f"default_rider_speed must divide {LATTICE_STEP}")

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> "SystemConfig":
        """Load configuration from a JSON file.

        Missing files fall back to defaults. Invalid files are logged and the
        defaults are used instead, so the system always starts.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            A validated SystemConfig instance.
        """
        config = cls(config_file_path=path)
        if not os.path.exists(path):
            logger.info("Configuration file %s not found; using defaults", path)
            config.validate()
            return config
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("top-level JSON value must be an object")
            valid = {f.name for f in fields(cls)} - {"config_file_path"}
            for key, value in data.items():
                if key in valid:
                    setattr(config, key, value)
                else:
                    logger.warning("Ignoring unknown configuration key '%s'", key)
            config.validate()
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.error("Invalid configuration %s (%s); using defaults", path, exc)
            config = cls(config_file_path=path)
        return config

    def to_dict(self) -> dict:
        """Return the configuration as a plain dictionary."""
        return asdict(self)
