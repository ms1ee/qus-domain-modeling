"""Grid map model and grid-based path planning.

The city is an 800x800 unit square divided into an 8x8 grid of 100x100
cells. Streets lie on the grid lines, i.e. every point whose x or y
coordinate is a multiple of 100. Restaurants and customers are placed at
cell centres (``100 * k + 50``). Routes are built from axis-aligned
segments that move along the streets whenever possible.
"""

import logging
import math
from collections import deque

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = MAP_SIZE // CELL_SIZE


def validate_point(x, y):
    """Validate that ``x`` and ``y`` are integers within the map range.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Tuple ``(x, y)`` of ints.

    Raises:
        ValueError: If a coordinate is not an integer or is out of range.
    """
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate must be an integer, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"coordinate {value} is out of range 0-{MAP_SIZE}"
            )
    return int(x), int(y)


def cell_index_of(x, y):
    """Return the grid cell index ``(grid_x, grid_y)`` containing a point.

    Values at the far boundary (800) are clamped into the last cell.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Tuple of cell indices, each in ``0..7``.
    """
    gx = min(max(x // CELL_SIZE, 0), GRID_CELLS - 1)
    gy = min(max(y // CELL_SIZE, 0), GRID_CELLS - 1)
    return gx, gy


def cell_center_of(x, y):
    """Convert a coordinate to the centre point of its grid cell.

    Implements ``center_x = (grid_x // 100) * 100 + 50``.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    gx, gy = cell_index_of(x, y)
    return gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2


def nearest_intersection(x, y):
    """Return the nearest street intersection (multiple of 100) to a point.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Tuple ``(node_x, node_y)`` of intersection coordinates.
    """
    nx = (x + CELL_SIZE // 2) // CELL_SIZE * CELL_SIZE
    ny = (y + CELL_SIZE // 2) // CELL_SIZE * CELL_SIZE
    return (
        min(max(nx, 0), MAP_SIZE),
        min(max(ny, 0), MAP_SIZE),
    )


class GridCell:
    """One 100x100 cell of the grid map.

    Attributes:
        grid_x: Column index (0-7).
        grid_y: Row index (0-7).
        center_x: X coordinate of the cell centre.
        center_y: Y coordinate of the cell centre.
        is_street: Whether the cell interior is a street. Streets are the
            grid lines bounding the cells, so cell interiors are blocks.
    """

    def __init__(self, grid_x, grid_y):
        """Create a cell at the given index.

        Args:
            grid_x: Column index.
            grid_y: Row index.
        """
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.center_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = grid_y * CELL_SIZE + CELL_SIZE // 2
        self.is_street = False


class GridMap:
    """The 8x8 grid representing the 800x800 coordinate system.

    Attributes:
        width: Map width in units.
        height: Map height in units.
        cell_size: Side length of one cell in units.
        cols: Number of cell columns.
        rows: Number of cell rows.
        cells: Dictionary mapping ``(grid_x, grid_y)`` to :class:`GridCell`.
    """

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        """Build the grid and all of its cells.

        Args:
            width: Map width in units.
            height: Map height in units.
            cell_size: Side length of one cell in units.
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cols = width // cell_size
        self.rows = height // cell_size
        self.cells = {}
        for gx in range(self.cols):
            for gy in range(self.rows):
                self.cells[(gx, gy)] = GridCell(gx, gy)

    @staticmethod
    def center_of(x, y):
        """Return the centre of the cell containing ``(x, y)``.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple ``(center_x, center_y)``.
        """
        return cell_center_of(x, y)

    def cell_at(self, x, y):
        """Return the :class:`GridCell` containing ``(x, y)``.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            The matching GridCell instance.
        """
        return self.cells[cell_index_of(x, y)]

    def is_street_point(self, x, y):
        """Return True if ``(x, y)`` lies on a street (grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Boolean flag.
        """
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def in_bounds(self, x, y):
        """Return True if ``(x, y)`` lies inside the map.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Boolean flag.
        """
        return 0 <= x <= self.width and 0 <= y <= self.height


class Route:
    """A planned route made of connected axis-aligned segments.

    Attributes:
        start: Starting point ``(x, y)``.
        waypoints: Ordered list of points after the start, ending at the goal.
        segments: List of ``((x1, y1), (x2, y2))`` tuples.
        total_distance: Total travelled length in units.
        estimated_time: Ticks needed at the planned speed.
        special_case: True if the route uses an off-street access leg.
    """

    def __init__(self, start, waypoints, speed, special_case=False):
        """Build a route and compute its segments, distance and time.

        Args:
            start: Starting point ``(x, y)``.
            waypoints: Ordered points to visit after the start.
            speed: Movement speed in units per tick.
            special_case: Whether an off-street access leg is used.
        """
        self.start = (int(start[0]), int(start[1]))
        self.waypoints = [(int(p[0]), int(p[1])) for p in waypoints]
        self.special_case = special_case
        self.segments = []
        total = 0.0
        prev = self.start
        for point in self.waypoints:
            self.segments.append((prev, point))
            total += math.hypot(point[0] - prev[0], point[1] - prev[1])
            prev = point
        self.total_distance = total
        if speed > 0 and total > 0:
            self.estimated_time = math.ceil(total / speed)
        else:
            self.estimated_time = 0


class PathPlanner:
    """Grid-based path planner that prefers street movement.

    The planner routes riders through street intersections using a
    breadth-first search on the 9x9 lattice of intersections (which yields
    shortest Manhattan paths). Off-street access legs are used only to reach
    a point inside a cell from its nearest street. Such legs set the
    ``special_case`` flag of the returned route.

    Attributes:
        grid_map: The :class:`GridMap` the planner operates on.
    """

    def __init__(self, grid_map=None):
        """Create a planner.

        Args:
            grid_map: Optional GridMap. A default 8x8 map is created when
                omitted.
        """
        self.grid_map = grid_map or GridMap()

    def nearest_node(self, x, y):
        """Return the nearest street intersection for a point.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Tuple ``(node_x, node_y)``.
        """
        return nearest_intersection(x, y)

    def _start_access(self, start, node):
        """Build the legs that take a rider from its position onto a street.

        The rider first moves vertically to the street row of ``node`` and
        then horizontally along that street to the node.

        Args:
            start: Current position ``(x, y)``.
            node: Target intersection.

        Returns:
            Tuple ``(points, off_street)``.
        """
        x, y = start
        nx, ny = node
        off_street = (x % self.grid_map.cell_size != 0) and (y != ny)
        return [(x, ny), (nx, ny)], off_street

    def _goal_access(self, goal, node):
        """Build the legs that take a rider from a street into a goal cell.

        The rider travels along the street to the goal's column and then
        moves vertically into the goal point.

        Args:
            goal: Destination point ``(x, y)``.
            node: Intersection the rider leaves from.

        Returns:
            Tuple ``(points, off_street)``.
        """
        gx, gy = goal
        _, ny = node
        off_street = (gx % self.grid_map.cell_size != 0) and (ny != gy)
        return [(gx, ny), (gx, gy)], off_street

    def _street_path(self, src, dst):
        """Find the shortest street path between two intersections.

        Args:
            src: Source intersection ``(x, y)``.
            dst: Destination intersection ``(x, y)``.

        Returns:
            List of intersections from ``src`` to ``dst`` inclusive.

        Raises:
            ValueError: If no path exists (should not happen on a full grid).
        """
        if src == dst:
            return [src]
        step = self.grid_map.cell_size
        width = self.grid_map.width
        height = self.grid_map.height
        prev = {src: None}
        queue = deque([src])
        while queue:
            current = queue.popleft()
            if current == dst:
                break
            cx, cy = current
            for dx, dy in ((step, 0), (-step, 0), (0, step), (0, -step)):
                nxt = (cx + dx, cy + dy)
                if (0 <= nxt[0] <= width and 0 <= nxt[1] <= height
                        and nxt not in prev):
                    prev[nxt] = current
                    queue.append(nxt)
        if dst not in prev:
            raise ValueError(f"no street path from {src} to {dst}")
        path = []
        node = dst
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
        return path

    def plan(self, start, goal, speed=10):
        """Plan a route from ``start`` to ``goal`` that prefers streets.

        Args:
            start: Starting point ``(x, y)``.
            goal: Destination point ``(x, y)``.
            speed: Movement speed used to estimate travel time.

        Returns:
            A :class:`Route` whose waypoints end at ``goal``.

        Raises:
            ValueError: If a point is not a valid map coordinate.
        """
        start = validate_point(*start)
        goal = validate_point(*goal)
        if not (self.grid_map.in_bounds(*start)
                and self.grid_map.in_bounds(*goal)):
            raise ValueError("route endpoints must lie inside the map")

        start_node = self.nearest_node(*start)
        goal_node = self.nearest_node(*goal)
        start_points, start_off = self._start_access(start, start_node)
        goal_points, goal_off = self._goal_access(goal, goal_node)
        street = self._street_path(start_node, goal_node)

        waypoints = start_points + street[1:] + goal_points
        cleaned = []
        prev = start
        for point in waypoints:
            if point != prev:
                cleaned.append(point)
                prev = point
        route = Route(start, cleaned, speed,
                      special_case=start_off or goal_off)
        logger.debug("Planned route %s -> %s with %d waypoints",
                     start, goal, len(cleaned))
        return route
