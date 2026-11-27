"""System-wide constants and configurable parameters.

Map geometry constants are fixed by the PRD (800x800 units, 100-unit cells).
Economic and capacity parameters can be overridden through a JSON file.
"""

import json
import logging
import os
from dataclasses import dataclass, fields

import globalvar

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE          # 8 x 8 cells
LATTICE_STEP = 50                         # movement resolution (half a cell)
DEFAULT_CONFIG_FILE = "system_config.json"
MAX_LOG_ENTRIES = 500                     # per-rider event log cap (memory bound)


@dataclass
class SystemConfig:
    """Tunable system parameters.

    Attributes:
        initial_funds: Starting system funds.
        recruitment_cost: Funds deducted for each newly recruited rider.
        default_rider_speed: Movement speed in units per tick.
        max_riders: Upper bound on concurrently employed riders.
        max_orders_per_rider: Maximum queued orders per rider.
        load_penalty: Score penalty per already-assigned order.
        max_tick_batch: Largest number of ticks allowed in one ``tick`` command.
    """

    initial_funds: int = 1000
    recruitment_cost: int = 300
    default_rider_speed: int = 50
    max_riders: int = 10
    max_orders_per_rider: int = 3
    load_penalty: int = 200
    max_tick_batch: int = 1000


def load_config(path: str = DEFAULT_CONFIG_FILE) -> SystemConfig:
    """Load system parameters from a JSON file, falling back to defaults.

    The file may either be a flat object or contain the parameters under a
    ``"system"`` key. Unknown or invalid entries are logged and ignored.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A ``SystemConfig`` instance with the loaded or default values.
    """
    cfg = SystemConfig()
    if not os.path.exists(path):
        logger.info("Config file %s not found; using defaults.", path)
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config %s (%s); using defaults.", path, exc)
        return cfg
    if not isinstance(data, dict):
        logger.warning("Config file %s must contain a JSON object; using defaults.", path)
        return cfg
    section = data.get("system", data)
    if not isinstance(section, dict):
        logger.warning("Config section 'system' must be an object; using defaults.")
        return cfg

    valid_keys = {f.name for f in fields(SystemConfig)}
    for key, value in section.items():
        if key not in valid_keys:
            logger.warning("Unknown config key %r ignored.", key)
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            logger.warning("Invalid value %r for config key %r ignored.", value, key)
            continue
        setattr(cfg, key, value)
    return cfg


def get_config() -> SystemConfig:
    """Return the configuration stored in the global variable table.

    Returns:
        The active ``SystemConfig``; defaults if the system is not initialised.
    """
    cfg = globalvar.get_value("config")
    return cfg if isinstance(cfg, SystemConfig) else SystemConfig()
