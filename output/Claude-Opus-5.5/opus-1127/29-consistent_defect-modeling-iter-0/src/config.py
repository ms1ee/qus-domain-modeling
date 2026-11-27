"""Static configuration constants for the dispatch simulator."""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE  # 8x8 cells

INITIAL_FUNDS = 1000
RECRUITMENT_COST = 500
RECRUITMENT_THRESHOLD = 300

RIDER_SPEED = 10
RIDER_START_X = 400
RIDER_START_Y = 400

DISPLAY_SIZE = 16  # ASCII map is 16x16 characters

COORD_MIN = 0
COORD_MAX = 800

DEFAULT_CONFIG = {
    "initial_funds": INITIAL_FUNDS,
    "recruitment_cost": RECRUITMENT_COST,
    "recruitment_threshold": RECRUITMENT_THRESHOLD,
    "rider_speed": RIDER_SPEED,
    "rider_start_x": RIDER_START_X,
    "rider_start_y": RIDER_START_Y,
}
