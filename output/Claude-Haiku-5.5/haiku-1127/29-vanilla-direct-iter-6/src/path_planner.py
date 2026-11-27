"""Grid-based path planning for riders.

The map is an 800x800 unit plane divided into an 8x8 grid of 100x100 cells.
Lines whose x or y coordinate is a multiple of 100 are streets. Restaurant
and customer locations are cell centers (e.g. 150, 250, ...). Movement is
axis-aligned (horizontal or vertical) and prefers following streets.
"""

GRID_SIZE = 800
CELL_SIZE = 100
GRID_DIM = GRID_SIZE // CELL_SIZE


def is_on_street(value: int) -> bool:
    """Return True if a coordinate lies on a grid street line.

    Args:
        value: One coordinate (x or y) in units.

    Returns:
        True when the value is a multiple of the cell size.
    """
    return value % CELL_SIZE == 0


def cell_index(value: int) -> int:
    """Return the grid index (0-7) containing a coordinate.

    Values at or beyond the map edge are clamped to the last cell.

    Args:
        value: One coordinate in units.

    Returns:
        Integer cell index between 0 and GRID_DIM - 1.
    """
    return min(max(int(value), 0) // CELL_SIZE, GRID_DIM - 1)


def cell_center(value: int) -> int:
    """Convert a coordinate to the center of its grid cell.

    Implements ``center = (grid // 100) * 100 + 50`` with clamping so that
    the map edge value 800 maps to the center of the last cell (750).

    Args:
        value: One coordinate in units (0-800).

    Returns:
        The center coordinate of the containing cell.
    """
    return cell_index(value) * CELL_SIZE + CELL_SIZE // 2


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


class PathPlanner:
    """Computes routes and single-unit movement steps on the street grid.

    Rules:
        * Movement is horizontal or vertical only (right-angle turns).
        * A rider that stands on a street line (x multiple of 100) but
          not on a horizontal street moves along that street first.
        * Otherwise horizontal movement is preferred first.
        * When the rider is directly above or below the target, it moves
          straight vertically (special case).
    """

    def __init__(self, grid_size: int = GRID_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a planner for a grid of the given size.

        Args:
            grid_size: Map width/height in units.
            cell_size: Size of one grid cell in units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if the point lies inside the map (0..grid_size)."""
        return 0 <= x <= self.grid_size and 0 <= y <= self.grid_size

    def route(self, start: tuple, end: tuple) -> list:
        """Return a right-angle waypoint list from ``start`` to ``end``.

        The corner is chosen so that the first segment follows a street when
        possible.

        Args:
            start: (x, y) starting point.
            end: (x, y) destination point.

        Returns:
            List of (x, y) waypoints beginning with ``start`` and ending with
            ``end`` (consecutive duplicates removed).
        """
        sx, sy = start
        ex, ey = end
        if sx != ex and sy != ey and is_on_street(sx) and not is_on_street(sy):
            corner = (sx, ey)
        else:
            corner = (ex, sy)
        points = [(sx, sy)]
        for point in (corner, (ex, ey)):
            if point != points[-1]:
                points.append(point)
        return points

    @staticmethod
    def route_length(points: list) -> int:
        """Return the total Manhattan length of an axis-aligned route.

        Args:
            points: List of (x, y) waypoints.

        Returns:
            Total travelled distance in units.
        """
        total = 0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total

    @staticmethod
    def next_step(x: int, y: int, tx: int, ty: int) -> tuple:
        """Return the position after moving exactly one unit toward a target.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.

        Returns:
            (x, y) after one unit of axis-aligned movement. Returns the input
            position unchanged when already at the target.
        """
        if x == tx and y == ty:
            return x, y
        if x == tx:
            # Directly above or below the target: move straight vertically.
            return x, y + _sign(ty - y)
        if y == ty:
            return x + _sign(tx - x), y
        if is_on_street(x) and not is_on_street(y):
            return x, y + _sign(ty - y)
        return x + _sign(tx - x), y
