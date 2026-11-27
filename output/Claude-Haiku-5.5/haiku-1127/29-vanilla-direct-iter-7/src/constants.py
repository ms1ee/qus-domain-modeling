"""Shared constants for the food delivery dispatch simulator.

All numeric parameters from the PRD live here so that every module uses the
same values and so that they can be changed in one place.
"""

# Map geometry ---------------------------------------------------------------
MAP_SIZE = 800          # Coordinate range is 0..MAP_SIZE (inclusive).
CELL_SIZE = 100         # Each grid cell is CELL_SIZE x CELL_SIZE units.
GRID_DIM = 8            # 8 x 8 grid of cells.

# Funds and recruitment -------------------------------------------------------
INITIAL_FUNDS = 1000
RECRUIT_COST = 300
RECRUIT_MIN_FUNDS = 300

# Rider defaults --------------------------------------------------------------
RIDER_START_X = 435
RIDER_START_Y = 385
RIDER_SPEED = 10        # Units per tick.

# Rider states ----------------------------------------------------------------
STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

# Order statuses --------------------------------------------------------------
ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKING_UP = "picking_up"
ORDER_DELIVERING = "delivering"
ORDER_COMPLETED = "completed"

# Conflict / deadlock avoidance ------------------------------------------------
MAX_BLOCKED_WAIT = 3    # Ticks a rider waits for a blocked tile before forcing progress.

# Assignment ------------------------------------------------------------------
LOAD_PENALTY = 150.0    # Score penalty per already-queued order (load balancing).

# Simulation safety limit ------------------------------------------------------
MAX_SIM_TICKS = 5000
