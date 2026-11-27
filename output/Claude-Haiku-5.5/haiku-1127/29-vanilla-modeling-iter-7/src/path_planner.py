"""Grid-based path planning for the 800x800 street map.

The map is divided into an 8x8 grid of 100x100 cells. Grid lines at
multiples of 100 are streets. A rider that is off the street network first
moves to the nearest street, then travels along streets using right-angle
turns, and finally enters the target cell along its access lane.
"""

GRID_SIZE = 800
CELL_SIZE = 100


def clamp_coordinate(value):
    """Clamp a coordinate into the valid map range and return an int.

    Args:
        value: Raw coordinate value.

    Returns:
        Integer coordinate within ``[0, GRID_SIZE]``.
    """
    return max(0, min(GRID_SIZE, int(value)))


def is_street_point(x, y):
    """Return True if the point lies on a street (grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True when x or y is a multiple of ``CELL_SIZE``.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def nearest_street_coordinate(value):
    """Return the closest grid line coordinate to ``value``.

    Args:
        value: A single axis coordinate.

    Returns:
        The nearest multiple of ``CELL_SIZE`` within the map bounds.
    """
    return clamp_coordinate(((value + CELL_SIZE // 2) // CELL_SIZE) * CELL_SIZE)


def _horizontal_steps(x0, y, x1):
    """Return unit-step points moving horizontally from x0 to x1 (exclusive of start)."""
    if x0 == x1:
        return []
    step = 1 if x1 > x0 else -1
    return [(x, y) for x in range(x0 + step, x1 + step, step)]


def _vertical_steps(x, y0, y1):
    """Return unit-step points moving vertically from y0 to y1 (exclusive of start)."""
    if y0 == y1:
        return []
    step = 1 if y1 > y0 else -1
    return [(x, y) for y in range(y0 + step, y1 + step, step)]


def plan_path(sx, sy, tx, ty):
    """Plan a unit-step route from ``(sx, sy)`` to ``(tx, ty)``.

    The route first snaps an off-street start onto the nearest street, then
    travels along the street with right-angle turns. Special case: when the
    rider is directly above or below the target, only a straight vertical
    segment is produced.

    Args:
        sx: Start x coordinate.
        sy: Start y coordinate.
        tx: Target x coordinate.
        ty: Target y coordinate.

    Returns:
        List of ``(x, y)`` tuples, one per unit of movement, excluding the
        start point and including the target. Empty if already at target.
    """
    sx, sy = clamp_coordinate(sx), clamp_coordinate(sy)
    tx, ty = clamp_coordinate(tx), clamp_coordinate(ty)
    path = []
    cx, cy = sx, sy

    if not is_street_point(cx, cy):
        ny = nearest_street_coordinate(cy)
        nx = nearest_street_coordinate(cx)
        if abs(ny - cy) <= abs(nx - cx):
            path.extend(_vertical_steps(cx, cy, ny))
            cy = ny
        else:
            path.extend(_horizontal_steps(cx, cy, nx))
            cx = nx

    if cy % CELL_SIZE == 0:
        # On a horizontal street: travel along it, then enter the target column.
        path.extend(_horizontal_steps(cx, cy, tx))
        cx = tx
        path.extend(_vertical_steps(cx, cy, ty))
    else:
        # On a vertical street: travel along it, then enter the target row.
        path.extend(_vertical_steps(cx, cy, ty))
        cy = ty
        path.extend(_horizontal_steps(cx, cy, tx))
    return path


def estimate_route(sx, sy, restaurant, customer):
    """Return the full route from a rider position through pickup to delivery.

    Args:
        sx: Rider x coordinate.
        sy: Rider y coordinate.
        restaurant: ``(x, y)`` restaurant grid point.
        customer: ``(x, y)`` customer grid point.

    Returns:
        Concatenated list of unit-step route points.
    """
    to_restaurant = plan_path(sx, sy, restaurant[0], restaurant[1])
    to_customer = plan_path(restaurant[0], restaurant[1], customer[0], customer[1])
    return to_restaurant + to_customer


class PathPlanner:
    """Object wrapper around the grid path planning functions.

    Attributes:
        prioritize_streets: When True, routes prefer street segments.
    """

    def __init__(self, prioritize_streets=True):
        """Create a planner.

        Args:
            prioritize_streets: Whether to prioritize street movement.
        """
        self.prioritize_streets = prioritize_streets

    def plan(self, sx, sy, tx, ty):
        """Plan a route; see :func:`plan_path`."""
        return plan_path(sx, sy, tx, ty)

    def estimate_route(self, sx, sy, restaurant, customer):
        """Plan a pickup-and-delivery route; see :func:`estimate_route`."""
        return estimate_route(sx, sy, restaurant, customer)
