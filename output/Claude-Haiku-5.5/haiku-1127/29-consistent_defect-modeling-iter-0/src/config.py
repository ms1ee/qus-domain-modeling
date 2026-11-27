"""Central configuration constants for the food delivery dispatch simulator.

All tunable system parameters live here so that they can be adjusted in a
single place without touching the business logic.
"""

# ---------------------------------------------------------------------------
# Map geometry
# ---------------------------------------------------------------------------
MAP_SIZE = 800          # Map is 800x800 units.
CELL_SIZE = 100         # Each grid cell is 100x100 units.
GRID_DIMENSION = 8      # 8x8 grid of cells (64 cells).
COORD_MIN = 0           # Smallest valid coordinate for user input.
COORD_MAX = 800         # Largest valid coordinate for user input.

# ---------------------------------------------------------------------------
# Funds and recruitment
# ---------------------------------------------------------------------------
INITIAL_FUNDS = 1000        # Starting system funds.
RECRUIT_MIN_FUNDS = 300     # Funds required before a rider may be recruited.
RECRUIT_COST = 500          # Cost deducted for each recruited rider.

# ---------------------------------------------------------------------------
# Rider defaults
# ---------------------------------------------------------------------------
RIDER_START_X = 400         # Riders spawn on the road at (400, 400).
RIDER_START_Y = 400
RIDER_SPEED = 20            # Movement speed in units per tick.

# ---------------------------------------------------------------------------
# Rider states
# ---------------------------------------------------------------------------
STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

# ---------------------------------------------------------------------------
# Order statuses
# ---------------------------------------------------------------------------
ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_COMPLETED = "completed"

# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
DEFAULT_STATE_FILE = "dispatch_state.json"
MAX_TICKS_PER_COMMAND = 10000
