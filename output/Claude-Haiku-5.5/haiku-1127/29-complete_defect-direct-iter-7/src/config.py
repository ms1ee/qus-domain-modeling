"""System-wide configuration constants and the JSON configuration loader.

All tunable parameters live in this module.  Parameters listed in
OVERRIDABLE_PARAMETERS may be replaced at start-up from a JSON file (see
:func:`load_config`).

Economic model used by the simulator:
    * Every accepted order adds ORDER_FEE to the system funds.
    * When the funds reach RECRUIT_THRESHOLD a new rider is recruited and
      RIDER_COST is deducted from the funds.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("dispatch.config")

# Map geometry (800x800 units, 8x8 grid of 100x100 cells).
MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8

# Economy and recruitment.
RECRUIT_THRESHOLD = 300
RIDER_COST = 300
ORDER_FEE = 100

# Rider behaviour.
DEFAULT_SPEED = 100          # units per tick
MAX_ORDERS_PER_RIDER = 2
LOAD_PENALTY = 200           # distance-equivalent penalty per queued order
WAIT_REPLAN_TICKS = 3        # blocked this many ticks -> try alternate route
WAIT_GIVEUP_TICKS = 6        # blocked this many ticks -> proceed (deadlock break)

# Bookkeeping limits.
HISTORY_LIMIT = 200          # completed orders and command history kept
LOG_LIMIT = 1000             # rider log entries kept per rider
MAX_WAIT_COMMAND = 1000      # largest number of ticks the 'wait' command accepts

OVERRIDABLE_PARAMETERS = (
    "RECRUIT_THRESHOLD",
    "RIDER_COST",
    "ORDER_FEE",
    "DEFAULT_SPEED",
    "MAX_ORDERS_PER_RIDER",
    "LOAD_PENALTY",
    "WAIT_REPLAN_TICKS",
    "WAIT_GIVEUP_TICKS",
    "HISTORY_LIMIT",
    "LOG_LIMIT",
)


def get_parameters() -> dict:
    """Return the current values of all overridable parameters.

    Returns:
        dict: Mapping of parameter name to its current integer value.
    """
    module_globals = globals()
    return {name: module_globals[name] for name in OVERRIDABLE_PARAMETERS}


def load_config(path: str) -> dict:
    """Load parameter overrides from a JSON configuration file.

    The file may either contain the parameters at top level or under a
    "parameters" key.  Invalid values are ignored with a warning.  A missing
    or unreadable file leaves the defaults untouched.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        dict: The parameters that were actually applied.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.info("No configuration file at %s; using defaults.", path)
        return {}
    except (OSError, ValueError) as exc:
        logger.error("Could not read configuration file %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        logger.error("Configuration file %s must contain a JSON object.", path)
        return {}

    params = data.get("parameters", data)
    if not isinstance(params, dict):
        logger.error("'parameters' in %s must be a JSON object.", path)
        return {}

    applied = {}
    module_globals = globals()
    for name in OVERRIDABLE_PARAMETERS:
        if name not in params:
            continue
        value = params[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            logger.warning("Ignoring invalid value for %s: %r", name, value)
            continue
        module_globals[name] = value
        applied[name] = value
    logger.info("Applied configuration overrides: %s", applied)
    return applied
