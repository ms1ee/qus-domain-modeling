"""Shared constants for the food delivery dispatch simulator.

All numeric parameters of the PRD live here so that they can be tuned in a
single place without touching the algorithms.
"""

MAP_SIZE = 800
"""Edge length of the simulated map in coordinate units (0-800)."""

CELL_SIZE = 100
"""Edge length of one grid cell in coordinate units."""

GRID_SIZE = MAP_SIZE // CELL_SIZE
"""Number of grid cells along each axis (8x8 grid)."""

INITIAL_FUNDS = 1000
"""System funds at start-up."""

RIDER_COST = 300
"""Funds deducted for every recruited rider."""

RIDER_MIN_FUNDS = 300
"""Minimum funds required before a rider may be recruited."""

RIDER_SPAWN_X = 435
RIDER_SPAWN_Y = 385
"""Initial coordinates of every newly recruited rider."""

RIDER_SPEED = 10
"""Movement speed of a rider in coordinate units per tick."""

MAX_WAIT_TICKS = 3
"""Maximum number of ticks a rider waits for a blocked cell before proceeding."""

MAP_RESOLUTION = 25
"""Coordinate units represented by one character of the ASCII map."""

MAX_INPUT_ATTEMPTS = 3
"""Number of invalid coordinate entries accepted before cancelling an order."""

DEFAULT_SAVE_PATH = "dispatch_state.json"
"""Default file name used by the save command."""

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
"""Human readable names for rider states."""

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
"""Format used for diagnostic logging."""
