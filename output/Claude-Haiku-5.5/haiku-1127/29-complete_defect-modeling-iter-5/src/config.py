"""System configuration for the food delivery dispatch simulator.

Parameters have sensible defaults and can be overridden through an optional
JSON configuration file passed on the command line (``--config``).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, fields
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """Tunable parameters of the dispatch system.

    Attributes:
        recruitment_threshold: Funds needed before a new rider is recruited.
        recruitment_cost: Funds deducted for each recruited rider.
        order_fee: Funds credited to the system when an order is accepted.
        initial_funds: Funds available at startup.
        map_size: Side length of the square map in units.
        cell_size: Side length of one grid cell in units.
        default_speed: Movement speed of new riders in units per tick.
        load_penalty: Distance penalty added per already-assigned order when
            choosing a rider, providing load balancing.
        max_tick_batch: Maximum number of ticks advanced by one command.
        history_file: JSON file used to persist the system state.
    """

    recruitment_threshold: int = 300
    recruitment_cost: int = 300
    order_fee: int = 100
    initial_funds: int = 0
    map_size: int = 800
    cell_size: int = 100
    default_speed: int = 100
    load_penalty: int = 100
    max_tick_batch: int = 1000
    history_file: str = "dispatch_history.json"

    def validate(self) -> None:
        """Check that the configuration values are internally consistent.

        Raises:
            ValueError: If any value is out of its valid range.
        """
        if self.map_size <= 0 or self.cell_size <= 0:
            raise ValueError("map_size and cell_size must be positive")
        if self.map_size % self.cell_size != 0:
            raise ValueError("map_size must be a multiple of cell_size")
        if self.default_speed <= 0:
            raise ValueError("default_speed must be positive")
        if self.recruitment_cost <= 0:
            raise ValueError("recruitment_cost must be positive")
        if self.max_tick_batch <= 0:
            raise ValueError("max_tick_batch must be positive")
        if self.load_penalty < 0:
            raise ValueError("load_penalty must not be negative")


def load_config(path: Optional[str] = None) -> SystemConfig:
    """Load configuration from an optional JSON file.

    Unknown keys, unreadable files and invalid values are logged and ignored
    so that the program always starts with a usable configuration.

    Args:
        path: Path to a JSON file containing configuration overrides.

    Returns:
        A SystemConfig instance with defaults overridden by the file.
    """
    cfg = SystemConfig()
    if not path:
        return cfg
    if not os.path.exists(path):
        logger.warning("Config file %s not found; using defaults", path)
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config file %s (%s); using defaults", path, exc)
        return cfg
    if not isinstance(data, dict):
        logger.warning("Config file %s must contain a JSON object; using defaults", path)
        return cfg

    known = {field.name for field in fields(SystemConfig)}
    for key, value in data.items():
        if key not in known:
            logger.warning("Ignoring unknown config key %r", key)
            continue
        default = getattr(cfg, key)
        try:
            value = type(default)(value)
        except (TypeError, ValueError):
            logger.warning("Invalid value %r for config key %r; ignored", value, key)
            continue
        setattr(cfg, key, value)

    try:
        cfg.validate()
    except ValueError as exc:
        logger.warning("Invalid configuration (%s); using defaults", exc)
        return SystemConfig()
    return cfg


_active_config: Optional[SystemConfig] = None


def configure(path: Optional[str] = None) -> SystemConfig:
    """Load the configuration and make it the active one.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        The newly active SystemConfig.
    """
    global _active_config
    _active_config = load_config(path)
    return _active_config


def get_config() -> SystemConfig:
    """Return the active configuration, loading defaults if necessary.

    Returns:
        The active SystemConfig instance.
    """
    if _active_config is None:
        return configure(None)
    return _active_config
