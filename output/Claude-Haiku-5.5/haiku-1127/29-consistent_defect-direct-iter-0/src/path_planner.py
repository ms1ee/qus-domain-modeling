"""Grid-based path planning for the 800x800 street map.

The map is divided into 8x8 cells of 100x100 units. Streets are the grid
lines (points where x or y is a multiple of 100). Restaurants and customers
sit at integer-hundred intersections. Riders always move along streets, so
their routes are right-angle paths made of straight segments.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = MAP_SIZE // CELL_SIZE  # 8 cells per axis


class PathPlanner:
    """Stateless helper providing coordinate conversion and path logic."""

    @staticmethod
    def snap_to_grid(value):
        """Convert a raw coordinate to the top-left corner of its grid cell.

        Values are clamped to the map range first (0-800).

        Args:
            value: Raw coordinate (int-convertible).

        Returns:
            int: Coordinate that is a multiple of 100 within 0-800.
        """
        value = max(0, min(MAP_SIZE, int(value)))
        return min(MAP_SIZE, (value // CELL_SIZE) * CELL_SIZE)

    @classmethod
    def snap_point(cls, point):
        """Snap an ``(x, y)`` pair to grid cell corners.

        Args:
            point: Sequence of two coordinates.

        Returns:
            tuple[int, int]: Snapped point.
        """
        x, y = point
        return (cls.snap_to_grid(x), cls.snap_to_grid(y))

    @staticmethod
    def grid_cell(x, y):
        """Return the (column, row) grid cell containing a point.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            tuple[int, int]: Cell indices in the range 0-7.
        """
        col = min(max(int(x), 0), MAP_SIZE - 1) // CELL_SIZE
        row = min(max(int(y), 0), MAP_SIZE - 1) // CELL_SIZE
        return (col, row)

    @classmethod
    def grid_center(cls, x, y):
        """Return the center point of the cell containing ``(x, y)``.

        Uses ``center = (grid // 100) * 100 + 50``.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            tuple[int, int]: Center coordinates of the cell.
        """
        col, row = cls.grid_cell(x, y)
        return (col * CELL_SIZE + 50, row * CELL_SIZE + 50)

    @staticmethod
    def is_on_street(x, y):
        """Return True when the point lies on a street (grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            bool: True if x or y is a multiple of 100.
        """
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points.

        Args:
            a: ``(x, y)`` tuple.
            b: ``(x, y)`` tuple.

        Returns:
            int: ``|ax - bx| + |ay - by|``.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a, b):
        """Euclidean distance between two points.

        Args:
            a: ``(x, y)`` tuple.
            b: ``(x, y)`` tuple.

        Returns:
            float: ``sqrt((ax - bx)^2 + (ay - by)^2)``.
        """
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    @staticmethod
    def next_axis(x, y, tx, ty):
        """Decide which axis to move along next to reach the target.

        Special cases:
            * Target directly above/below (same x): move vertically only.
            * Target directly left/right (same y): move horizontally only.
            * Otherwise, move along the axis whose street the rider is on,
              which keeps every step on a street.

        Args:
            x, y: Current position.
            tx, ty: Target position.

        Returns:
            str | None: ``"x"``, ``"y"``, or None when already at target.
        """
        if (x, y) == (tx, ty):
            return None
        if x == tx:
            return "y"
        if y == ty:
            return "x"
        return "x" if y % CELL_SIZE == 0 else "y"

    @classmethod
    def step_towards(cls, x, y, tx, ty, speed):
        """Advance a position toward a target by up to ``speed`` units.

        The movement follows street lines only and may turn a right angle
        within the same tick if budget remains.

        Args:
            x, y: Current position.
            tx, ty: Target position.
            speed: Maximum distance to travel this tick.

        Returns:
            tuple[int, int]: New position.
        """
        budget = int(speed)
        while budget > 0 and (x, y) != (tx, ty):
            axis = cls.next_axis(x, y, tx, ty)
            if axis == "x":
                step = min(budget, abs(tx - x))
                x += step if tx > x else -step
            else:
                step = min(budget, abs(ty - y))
                y += step if ty > y else -step
            budget -= step
        return (x, y)

    @classmethod
    def plan_route(cls, start, targets):
        """Build the right-angle corner路径 from ``start`` through ``targets``.

        Riders do not block each other, so route planning is deterministic
        and free of deadlocks.

        Args:
            start: Starting ``(x, y)`` point.
            targets: Ordered list of ``(x, y)`` waypoints.

        Returns:
            list[tuple[int, int]]: Corner points including the start.
        """
        cx, cy = int(start[0]), int(start[1])
        points = [(cx, cy)]
        for tx, ty in targets:
            while (cx, cy) != (tx, ty):
                axis = cls.next_axis(cx, cy, tx, ty)
                if axis == "x":
                    cx = tx
                else:
                    cy = ty
                points.append((cx, cy))
        return points

    @classmethod
    def route_length(cls, points):
        """Total Manhattan length of a polyline.

        Args:
            points: List of ``(x, y)`` points.

        Returns:
            int: Sum of consecutive Manhattan distances.
        """
        return sum(cls.manhattan(a, b) for a, b in zip(points, points[1:]))
