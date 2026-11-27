"""System configuration parameters.

Default values are defined in ``DEFAULT_CONFIG``. An optional JSON file
(``config.json`` next to this module by default) may override any key whose
JSON value has the same type as the default.
"""

import json
import logging
import os

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG = {
    "map_size": 800,              # overall coordinate range (0..map_size)
    "cell_size": 100,             # size of one grid cell in units
    "initial_funds": 300,         # funds at system start (spawns one rider)
    "recruit_threshold": 300,     # funds needed to trigger rider recruitment
    "recruit_cost": 300,          # funds consumed by each recruited rider
    "order_fee": 100,             # funds earned for each placed order
    "rider_speed": 50,            # movement units per tick
    "max_orders_per_rider": 3,    # maximum queued orders per rider
    "history_size": 50,           # number of commands kept in history
    "save_on_exit": True,         # persist state to JSON on quit
    "save_file": "dispatch_state.json",
}

CONFIG = dict(DEFAULT_CONFIG)

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config(path=None):
    """Load configuration overrides from a JSON file.

    Args:
        path: Optional path to the JSON configuration file. Defaults to
            ``config.json`` located next to this module.

    Returns:
        The shared ``CONFIG`` dictionary (updated in place).
    """
    config_path = path or _DEFAULT_PATH
    if not os.path.exists(config_path):
        return CONFIG
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read configuration '%s': %s", config_path, exc)
        return CONFIG
    if not isinstance(data, dict):
        logger.error("Configuration file '%s' must contain a JSON object", config_path)
        return CONFIG
    for key, value in data.items():
        if key in DEFAULT_CONFIG and type(value) is type(DEFAULT_CONFIG[key]):
            CONFIG[key] = value
        else:
            logger.warning("Ignoring unknown or mistyped config key '%s'", key)
    return CONFIG
