"""Grid geometry constants and coordinate helpers.

The simulated map is 800x800 units, divided into an 8x8 grid of 100x100
cells. Lines at multiples of 100 are streets. Restaurant and customer
locations are converted to the centre point of their grid cell.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8

RIDER_SPAWN = (435, 385)
DEFAULT_RIDER_SPEED = 10
RECRUIT_COST = 300
INITIAL_FUNDS = 1000
MAX_ROUTE_TICKS = 2000


def validate_coordinate(value) -> int:
    """Validate that a coordinate is an integer within the map range.

    Args:
        value: The raw value to validate.

    Returns:
        The coordinate as an int.

    Raises:
        ValueError: If the value is not an integer or lies outside 0-800.
    """
    if isinstance(value, bool):
        raise ValueError(f"'{value}' is not an integer coordinate")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{value}' is not an integer coordinate") from None
    if str(value).strip() != str(number) and not isinstance(value, int):
        raise ValueError(f"'{value}' is not an integer coordinate")
    if number < 0 or number > MAP_SIZE:
        raise ValueError(
            f"coordinate {number} is out of range (0-{MAP_SIZE})"
        )
    return number


def to_cell_center(x, y) -> tuple:
    """Convert a raw coordinate pair to the centre of its grid cell.

    Values at or beyond the map edge (800) are clamped into the last cell.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        Tuple (center_x, center_y) with center = (v // 100) * 100 + 50.
    """
    cx = min(max(int(x), 0), MAP_SIZE - 1)
    cy = min(max(int(y), 0), MAP_SIZE - 1)
    center_x = (cx // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
    center_y = (cy // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2
    return center_x, center_y


def cell_index(x, y) -> tuple:
    """Return the (column, row) grid index of the cell containing a point.

    Args:
        x: x coordinate.
        y: y coordinate.

    Returns:
        Tuple (column, row), each in range 0-7.
    """
    last = GRID_DIM - 1
    col = min(max(int(x) // CELL_SIZE, 0), last)
    row = min(max(int(y) // CELL_SIZE, 0), last)
    return col, row


def cell_label(x, y) -> str:
    """Return a human readable grid cell label such as '(col 1, row 2)'."""
    col, row = cell_index(x, y)
    return f"(col {col}, row {row})"


def is_street(x, y) -> bool:
    """Return True if the point lies on a street (grid line)."""
    return int(x) % CELL_SIZE == 0 or int(y) % CELL_SIZE == 0
