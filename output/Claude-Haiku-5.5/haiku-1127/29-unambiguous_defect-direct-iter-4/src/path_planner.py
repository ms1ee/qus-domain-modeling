"""Grid-based path planning for the food delivery simulator.

Coordinate system:
    * Map is 800x800 units divided into an 8x8 grid of 100x100 cells.
    * Streets lie on grid lines: a point is on a street when its x or y
      coordinate is a multiple of 100.
    * Intersections are points where both coordinates are multiples of 100
      (a 9x9 lattice of 81 nodes).
    * Order locations are converted to cell centers:
      ``center = (cell_index * 100 + 50)``.

Routes travel along streets between intersections (breadth-first search on
the lattice, which always prefers right-angle, street-aligned moves). The
final approach from a cell corner into a cell center is a single right-angle
turn.
"""

import logging
from collections import deque

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
CELL_HALF = CELL_SIZE // 2


def to_point(value):
    """Convert a 2-item sequence into an ``(int, int)`` tuple.

    Args:
        value: Sequence containing x and y.

    Returns:
        Tuple ``(x, y)`` of integers.
    """
    x, y = value
    return (int(x), int(y))


def clamp_coordinate(value):
    """Clamp a numeric coordinate into the map range ``[0, MAP_SIZE]``.

    Args:
        value: Number to clamp.

    Returns:
        Integer coordinate within the map bounds.
    """
    number = int(round(float(value)))
    return max(0, min(MAP_SIZE, number))


def cell_index(coordinate):
    """Return the grid cell index (0-7) containing ``coordinate``.

    Args:
        coordinate: Map coordinate in units.

    Returns:
        Cell index clamped to ``[0, GRID_SIZE - 1]``.
    """
    return min(max(int(coordinate) // CELL_SIZE, 0), GRID_SIZE - 1)


def to_cell_center(x, y):
    """Map an input coordinate pair onto the center of its grid cell.

    Implements ``center_x = (grid_x // 100) * 100 + 50``.

    Args:
        x: Input x coordinate.
        y: Input y coordinate.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    return (cell_index(x) * CELL_SIZE + CELL_HALF,
            cell_index(y) * CELL_SIZE + CELL_HALF)


def cell_corner(x, y):
    """Return the lower-left street intersection of the cell containing (x, y).

    Args:
        x: Map x coordinate.
        y: Map y coordinate.

    Returns:
        Tuple ``(corner_x, corner_y)`` of an intersection.
    """
    return (cell_index(x) * CELL_SIZE, cell_index(y) * CELL_SIZE)


def is_street(x, y):
    """Return True if the point lies on a street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def is_intersection(x, y):
    """Return True if the point is a street intersection."""
    return x % CELL_SIZE == 0 and y % CELL_SIZE == 0


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: First point ``(x, y)``.
        b: Second point ``(x, y)``.

    Returns:
        Integer Manhattan distance.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def all_intersections():
    """Return all 81 street intersections of the map.

    Returns:
        List of ``(x, y)`` tuples in row-major order.
    """
    steps = range(GRID_SIZE + 1)
    return [(i * CELL_SIZE, j * CELL_SIZE) for i in steps for j in steps]


def l_path(src, dst):
    """Return right-angle waypoints from ``src`` to ``dst`` (horizontal first).

    The returned list excludes ``src`` and ends at ``dst``.

    Args:
        src: Start point.
        dst: Destination point.

    Returns:
        List of waypoints (may be empty when src == dst).
    """
    points = []
    if src[0] != dst[0]:
        points.append((dst[0], src[1]))
    if src[1] != dst[1]:
        points.append((dst[0], dst[1]))
    return points


def route_length(start, waypoints):
    """Return the total Manhattan length of a waypoint route.

    Args:
        start: Starting point.
        waypoints: Ordered list of points.

    Returns:
        Total length in map units.
    """
    total = 0
    previous = start
    for point in waypoints:
        total += manhattan(previous, point)
        previous = point
    return total


def _dedupe(points):
    """Remove consecutive duplicate points from a waypoint list."""
    result = []
    for point in points:
        if not result or result[-1] != point:
            result.append(point)
    return result


def _neighbors(node):
    """Yield the street-adjacent intersections of ``node``."""
    x, y = node
    for dx, dy in ((CELL_SIZE, 0), (-CELL_SIZE, 0), (0, CELL_SIZE), (0, -CELL_SIZE)):
        nx, ny = x + dx, y + dy
        if 0 <= nx <= MAP_SIZE and 0 <= ny <= MAP_SIZE:
            yield (nx, ny)


class PathPlanner:
    """Compute street-first routes between points on the 8x8 grid.

    The planner handles three kinds of starting positions:

    * On an intersection: routing begins from the node itself.
    * On a street segment: the rider first walks to one of the two bounding
      intersections (whichever yields the shorter total route).
    * Off the street (e.g. a cell center): the rider first leaves to the cell
      corner using a right-angle move.

    Destinations are reached through the cell corner of their cell and a final
    right-angle approach, so cell centers are entered from the street.
    """

    def plan(self, start, goal):
        """Return the ordered waypoints from ``start`` to ``goal``.

        Args:
            start: Current position ``(x, y)``.
            goal: Destination ``(x, y)``.

        Returns:
            List of waypoints ending at ``goal``. Empty if already there.
        """
        start = to_point(start)
        goal = to_point(goal)
        if start == goal:
            return []

        access = cell_corner(goal[0], goal[1])
        approach = l_path(access, goal)

        best = None
        for entry, prelude in self._entry_candidates(start):
            nodes = self._bfs(entry, access)
            if nodes is None:
                continue
            cost = route_length(start, prelude) + (len(nodes) - 1) * CELL_SIZE
            if best is None or cost < best[0]:
                best = (cost, prelude, nodes)

        if best is None:
            logger.warning("No street route from %s to %s; using direct path",
                           start, goal)
            return _dedupe(l_path(start, goal))

        _, prelude, nodes = best
        return _dedupe(prelude + nodes[1:] + approach)

    def _entry_candidates(self, start):
        """Return candidate ``(entry_node, prelude_points)`` pairs for a start."""
        x, y = start
        if is_intersection(x, y):
            return [(start, [])]
        if is_street(x, y):
            if x % CELL_SIZE == 0:
                low = (x, (y // CELL_SIZE) * CELL_SIZE)
                high = (x, low[1] + CELL_SIZE)
            else:
                low = ((x // CELL_SIZE) * CELL_SIZE, y)
                high = (low[0] + CELL_SIZE, y)
            candidates = []
            for node in (low, high):
                if 0 <= node[0] <= MAP_SIZE and 0 <= node[1] <= MAP_SIZE:
                    candidates.append((node, [node]))
            return candidates
        corner = cell_corner(x, y)
        return [(corner, l_path(start, corner))]

    @staticmethod
    def _bfs(source, target):
        """Breadth-first search over the intersection lattice.

        Returns:
            List of intersections from ``source`` to ``target`` inclusive,
            or None if unreachable.
        """
        if source == target:
            return [source]
        parent = {source: None}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for neighbor in _neighbors(node):
                if neighbor in parent:
                    continue
                parent[neighbor] = node
                if neighbor == target:
                    path = []
                    current = target
                    while current is not None:
                        path.append(current)
                        current = parent[current]
                    path.reverse()
                    return path
                queue.append(neighbor)
        return None
