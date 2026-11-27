"""Configuration constants for the food delivery dispatch simulator.

The tunable values listed in ``TUNABLE_PARAMS`` may be overridden at startup
through a JSON configuration file (see ``system.apply_config_file``).
Other modules read these values at call time (``config.NAME``) so that
overrides take effect everywhere.
"""

# ---------------------------------------------------------------------------
# Map and coordinate system
# ---------------------------------------------------------------------------
MAP_SIZE = 800                      # map spans 0..800 on both axes
CELL_SIZE = 100                     # each grid cell is 100x100 units
GRID_CELLS = MAP_SIZE // CELL_SIZE  # 8x8 grid
CELL_CENTER_OFFSET = CELL_SIZE // 2  # 50
COORD_MIN = 0
COORD_MAX = MAP_SIZE

# ---------------------------------------------------------------------------
# Economy and rider pool
# ---------------------------------------------------------------------------
INITIAL_FUNDS = 1000
RIDER_RECRUIT_COST = 100
MAX_RIDERS = 12
MAX_ORDERS_PER_RIDER = 3
DELIVERY_FEE = 30
LOAD_PENALTY = 150                  # score penalty per already-assigned order

# ---------------------------------------------------------------------------
# Rider movement
# ---------------------------------------------------------------------------
RIDER_SPEED_MIN = 8                 # units per tick
RIDER_SPEED_MAX = 15
MAX_RIDER_LOG = 2000                # cap on per-rider event log length

# ---------------------------------------------------------------------------
# Simulation control
# ---------------------------------------------------------------------------
MAX_SIMULATION_TICKS = 5000         # safety cap for a single 'start' command
MAX_MANUAL_TICKS = 1000             # maximum ticks for a single 'tick' command

# Rider status enumeration
STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
CONFIG_FILE = "dispatch_config.json"
STATE_FILE = "dispatch_state.json"
LOG_FILE = "dispatch.log"

# Parameters that may be overridden from the JSON configuration file.
TUNABLE_PARAMS = (
    "INITIAL_FUNDS",
    "RIDER_RECRUIT_COST",
    "MAX_RIDERS",
    "MAX_ORDERS_PER_RIDER",
    "DELIVERY_FEE",
    "LOAD_PENALTY",
    "RIDER_SPEED_MIN",
    "RIDER_SPEED_MAX",
    "MAX_SIMULATION_TICKS",
)
