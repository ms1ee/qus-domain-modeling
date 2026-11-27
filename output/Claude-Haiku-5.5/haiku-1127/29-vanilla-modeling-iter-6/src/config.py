"""System configuration loaded from an optional JSON file.

The JSON file may either be a flat object or contain a ``"system"`` object
holding the parameters. Unknown keys are ignored and invalid values fall
back to the defaults.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, fields

logger = logging.getLogger(__name__)


@dataclass
class Configuration:
    """Tunable simulation parameters.

    Attributes:
        initial_funds: Starting system funds.
        rider_recruitment_cost: Funds deducted per recruited rider.
        recruitment_fund_threshold: Minimum funds required to recruit.
        initial_rider_speed: Speed of new riders in units per tick.
        initial_rider_x: Spawn x coordinate for new riders.
        initial_rider_y: Spawn y coordinate for new riders.
        max_ticks_per_order: Safety limit when running an order to completion.
    """

    initial_funds: int = 1000
    rider_recruitment_cost: int = 300
    recruitment_fund_threshold: int = 300
    initial_rider_speed: int = 10
    initial_rider_x: int = 435
    initial_rider_y: int = 385
    max_ticks_per_order: int = 1000

    @classmethod
    def load(cls, path):
        """Load configuration from a JSON file.

        Args:
            path: Path to a JSON configuration file.

        Returns:
            A Configuration instance. Defaults are used for any missing or
            invalid entries, and when the file cannot be read.
        """
        config = cls()
        if not path or not os.path.exists(path):
            logger.warning("Config file %s not found; using defaults.", path)
            return config
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to read config %s: %s", path, exc)
            return config

        params = data.get("system", data) if isinstance(data, dict) else {}
        if not isinstance(params, dict):
            logger.error("Config %s has an invalid structure.", path)
            return config

        for field_info in fields(cls):
            if field_info.name not in params:
                continue
            try:
                setattr(config, field_info.name, int(params[field_info.name]))
            except (TypeError, ValueError):
                logger.error("Invalid value for %s; using default.",
                             field_info.name)
        return config

    def save(self, path):
        """Write the configuration to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            True on success, False when the file cannot be written.
        """
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"system": asdict(self)}, handle, indent=2)
            return True
        except OSError as exc:
            logger.error("Failed to write config %s: %s", path, exc)
            return False
