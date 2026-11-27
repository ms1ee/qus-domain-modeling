"""Shared constants, default parameters and coordinate helpers."""

import globalvar

MAP_SIZE = 800          # Map is 800x800 units.
CELL_SIZE = 100         # Each grid cell is 100x100 units.
GRID_DIM = 8            # 8x8 grid of cells (9x9 street intersections).

CONFIG_FILE = "dispatch_config.json"
STATE_FILE = "dispatch_state.json"
LOG_FILE = "dispatch.log"

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_PARAMS = {
    "initial_funds": 10000,   # Starting system funds.
    "recruit_cost": 1500,     # Cost deducted for each recruited rider.
    "max_riders": 10,         # Upper bound on the rider roster.
    "speed_min": 10,          # Minimum rider speed (units per tick).
    "speed_max": 20,          # Maximum rider speed (units per tick).
    "load_penalty": 300,      # Score penalty per active order a rider holds.
    "order_revenue": 500,     # Funds credited for each delivered order.
    "upkeep_per_rider": 1,    # Funds deducted per rider per tick.
}


def param(name: str):
    """Return a system parameter, falling back to its default value.

    Args:
        name: One of the keys of ``DEFAULT_PARAMS``.

    Returns:
        The configured value for ``name``.
    """
    params = globalvar.get_value("params") or {}
    if name in params:
        return params[name]
    return DEFAULT_PARAMS[name]


def is_valid_coordinate(value) -> bool:
    """Return True if ``value`` is an integer within the map bounds.

    Args:
        value: Candidate coordinate.

    Returns:
        True when ``value`` is an ``int`` (not ``bool``) in ``[0, MAP_SIZE]``.
    """
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAP_SIZE


def cell_center(x: int, y: int):
    """Return the centre point of the grid cell containing ``(x, y)``.

    Uses ``center = (coord // 100) * 100 + 50`` with the cell index clamped
    to the 8x8 grid.

    Args:
        x: X coordinate in map units.
        y: Y coordinate in map units.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    max_index = GRID_DIM - 1
    cx = min(x // CELL_SIZE, max_index) * CELL_SIZE + CELL_SIZE // 2
    cy = min(y // CELL_SIZE, max_index) * CELL_SIZE + CELL_SIZE // 2
    return cx, cy
