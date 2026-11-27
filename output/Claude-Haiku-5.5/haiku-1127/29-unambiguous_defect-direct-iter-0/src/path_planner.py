"""Grid-based path planning for the 800x800 delivery map.

The map is an 8x8 grid of 100x100 unit cells. Street lines and cell centres
lie at coordinates of the form ``50 + 100 * k``. Every cell centre is therefore
a street intersection, and every grid line is a navigable street. Movement
uses straight segments and right-angle turns only.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
ROAD_OFFSET = 50


class PathPlanner:
    """Pure path-planning helpers used by riders, orders and the display.

    All methods are stateless. Riders may share streets; because riders never
    block each other, no deadlock can occur, and conflicts are only a matter
    of shared road segments.
    """

    @staticmethod
    def cell_center(value):
        """Snap a raw coordinate to the centre of its grid cell.

        Implements ``center = (value // 100) * 100 + 50`` with clamping so
        that out-of-range values (such as 800) map to the nearest valid cell.

        Args:
            value: Raw integer coordinate.

        Returns:
            Integer centre coordinate in the range 50..750.
        """
        index = min(max(int(value), 0) // CELL_SIZE, GRID_DIM - 1)
        return index * CELL_SIZE + ROAD_OFFSET

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point lies on a street grid line.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True when ``x`` or ``y`` aligns with a street line.
        """
        return x % CELL_SIZE == ROAD_OFFSET or y % CELL_SIZE == ROAD_OFFSET

    @staticmethod
    def manhattan(a, b):
        """Return the Manhattan distance between two points.

        Args:
            a: Tuple ``(x, y)``.
            b: Tuple ``(x, y)``.

        Returns:
            Non-negative integer distance along streets.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def all_centres():
        """Return all 64 cell-centre coordinates.

        Returns:
            List of ``(x, y)`` tuples, one per grid cell.
        """
        return [
            (col * CELL_SIZE + ROAD_OFFSET, row * CELL_SIZE + ROAD_OFFSET)
            for row in range(GRID_DIM)
            for col in range(GRID_DIM)
        ]

    @classmethod
    def build_grid(cls):
        """Build the 8x8 grid map as rows of cell-centre coordinates.

        Returns:
            List of 8 rows, each a list of 8 ``(x, y)`` tuples.
        """
        return [
            [
                (col * CELL_SIZE + ROAD_OFFSET, row * CELL_SIZE + ROAD_OFFSET)
                for col in range(GRID_DIM)
            ]
            for row in range(GRID_DIM)
        ]

    @classmethod
    def plan_route(cls, start, goal, horizontal_first=True):
        """Plan an L-shaped street route between two points.

        When the goal is directly above or below (or beside) the start, the
        route degenerates to a straight segment (special case).

        Args:
            start: Tuple ``(x, y)`` of the starting point.
            goal: Tuple ``(x, y)`` of the destination.
            horizontal_first: Turn order; True moves along x first.

        Returns:
            List of waypoints beginning with ``start`` and ending with ``goal``.
        """
        sx, sy = start
        gx, gy = goal
        corner = (gx, sy) if horizontal_first else (sx, gy)
        route = [tuple(start)]
        for point in (corner, tuple(goal)):
            if point != route[-1]:
                route.append(point)
        return route

    @classmethod
    def multi_stop_route(cls, start, stops, horizontal_first=True):
        """Plan one continuous route visiting several stops in order.

        Args:
            start: Tuple ``(x, y)`` of the starting point.
            stops: Ordered iterable of ``(x, y)`` destinations.
            horizontal_first: Turn order used for every leg.

        Returns:
            Concatenated list of waypoints.
        """
        route = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            leg = cls.plan_route(current, stop, horizontal_first)
            route.extend(leg[1:])
            current = tuple(stop)
        return route

    @staticmethod
    def route_length(route):
        """Return the total street distance along a waypoint list.

        Args:
            route: List of ``(x, y)`` waypoints.

        Returns:
            Sum of Manhattan distances between consecutive waypoints.
        """
        total = 0
        for a, b in zip(route, route[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    @staticmethod
    def step_towards(x, y, tx, ty, speed):
        """Advance a position up to ``speed`` units along the street route.

        The rider first moves horizontally until its x matches the target,
        then vertically. Vertical movement therefore only happens along the
        target's street line, which keeps the rider on streets at all times.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum units to travel this tick.

        Returns:
            Tuple ``(new_x, new_y, moved)`` where ``moved`` is the distance
            actually travelled.
        """
        remaining = max(int(speed), 0)
        moved = 0
        if x != tx and remaining > 0:
            delta = min(abs(tx - x), remaining)
            x += delta if tx > x else -delta
            remaining -= delta
            moved += delta
        if y != ty and remaining > 0:
            delta = min(abs(ty - y), remaining)
            y += delta if ty > y else -delta
            remaining -= delta
            moved += delta
        return x, y, moved
