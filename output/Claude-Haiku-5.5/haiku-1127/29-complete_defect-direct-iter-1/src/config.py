"""System-wide constants and tunable parameters for the dispatch simulator.

Other modules access these values as attributes of this module (for example
``config.RIDER_COST``) so that values loaded from a JSON configuration file
via :func:`load_parameters` take effect everywhere.
"""

import json

# Map geometry: 800x800 units divided into an 8x8 grid of 100x100 cells.
MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
NODE_OFFSET = 50  # Cell centers (intersections) lie at 50, 150, ... 750.
SPAWN_POINT = (50, 50)

# Rider state enumeration.
STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking_up",
    STATE_DELIVERING: "delivering",
}

# Tunable economic and simulation parameters.
INITIAL_FUNDS = 300
RECRUIT_THRESHOLD = 300
RIDER_COST = 300
ORDER_FEE = 80
DEFAULT_SPEED = 50
MAX_ORDERS_PER_RIDER = 2
LOAD_PENALTY = 100
WAIT_LIMIT = 3
MAX_SIM_TICKS = 1000

DEFAULT_SNAPSHOT_PATH = "snapshot.json"
LOG_FILE = "dispatch.log"

_TUNABLE = (
    "INITIAL_FUNDS",
    "RECRUIT_THRESHOLD",
    "RIDER_COST",
    "ORDER_FEE",
    "DEFAULT_SPEED",
    "MAX_ORDERS_PER_RIDER",
    "LOAD_PENALTY",
    "WAIT_LIMIT",
    "MAX_SIM_TICKS",
)


def load_parameters(path):
    """Load tunable system parameters from a JSON configuration file.

    The file must contain a JSON object whose keys are parameter names
    (case-insensitive). Unknown keys are ignored.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        list[str]: Names of the parameters that were applied.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or a value is not an integer.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Configuration file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")

    module_globals = globals()
    applied = []
    for key, value in data.items():
        name = str(key).upper()
        if name not in _TUNABLE:
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Parameter {name} must be an integer.")
        module_globals[name] = value
        applied.append(name)
    return applied
