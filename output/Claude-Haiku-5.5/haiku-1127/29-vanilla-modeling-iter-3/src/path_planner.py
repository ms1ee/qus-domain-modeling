"""Grid-based path planning for riders on the 8x8 street map.

The map is an 800x800 coordinate system split into 100x100 cells. Streets lie
on the grid lines (x or y is a multiple of 100). Restaurant and customer
locations are cell centres (x and y equal 50 modulo 100). The planner builds a
search graph whose nodes are points spaced 50 units apart. Moving along a
street costs less than cutting across a cell interior, so routes prefer
streets. The resulting node path is expanded into axis-aligned waypoints, which
means every leg is either a straight horizontal or vertical run, including the
case where the target is directly above or below the rider.
"""

import heapq
import math
from typing import List, Sequence, Tuple

from config import CELL_SIZE, GRID_SIZE

Point = Tuple[int, int]

STREET_COST = 1
CROSS_COST = 2


def cell_center(value: int) -> int:
    """Return the centre coordinate of the grid cell containing ``value``.

    Implements ``center = (value // 100) * 100 + 50`` with the index clamped
    to the valid grid range so that the map edge (800) maps to the last cell.

    Args:
        value: A coordinate in the range 0-800.

    Returns:
        The centre coordinate of the containing cell.
    """
    index = int(value) // CELL_SIZE
    index = min(max(index, 0), GRID_SIZE - 1)
    return index * CELL_SIZE + CELL_SIZE // 2


def to_cell_center(point: Sequence[int]) -> Point:
    """Convert an ``(x, y)`` point to the centre of its grid cell.

    Args:
        point: Sequence of two integer coordinates.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    return (cell_center(point[0]), cell_center(point[1]))


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a: Point, b: Point) -> float:
    """Return the Euclidean distance between two points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


class PathPlanner:
    """Plans axis-aligned routes on the street grid.

    Attributes:
        grid_size: Number of cells per side (8).
        cell_size: Side length of one cell in units (100).
        step: Spacing of search nodes (50).
        max_coord: Largest coordinate on the map (800).
        nodes_per_side: Number of search nodes per row or column (17).
    """

    def __init__(self, grid_size: int = GRID_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a planner for a square grid.

        Args:
            grid_size: Number of cells per side.
            cell_size: Side length of each cell in units.

        Raises:
            ValueError: If either parameter is not positive or the cell size is odd.
        """
        if grid_size <= 0 or cell_size <= 0:
            raise ValueError("grid_size and cell_size must be positive")
        if cell_size % 2 != 0:
            raise ValueError("cell_size must be even")
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.step = cell_size // 2
        self.max_coord = grid_size * cell_size
        self.nodes_per_side = self.max_coord // self.step + 1

    def is_on_street(self, point: Point) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return point[0] % self.cell_size == 0 or point[1] % self.cell_size == 0

    def is_cell_center(self, point: Point) -> bool:
        """Return True if the point is the centre of a grid cell."""
        half = self.cell_size // 2
        return point[0] % self.cell_size == half and point[1] % self.cell_size == half

    def snap_to_node(self, point: Sequence[int]) -> Point:
        """Snap a point to the nearest search node inside the map.

        Args:
            point: Any point; coordinates are clamped to the map first.

        Returns:
            The nearest node as ``(x, y)``.
        """

        def snap(value: int) -> int:
            value = min(max(int(value), 0), self.max_coord)
            snapped = ((value + self.step // 2) // self.step) * self.step
            return min(snapped, self.max_coord)

        return (snap(point[0]), snap(point[1]))

    def _neighbors(self, node: Point):
        """Yield the four adjacent search nodes that stay inside the map."""
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = x + dx * self.step
            ny = y + dy * self.step
            if 0 <= nx <= self.max_coord and 0 <= ny <= self.max_coord:
                yield (nx, ny)

    def _edge_cost(self, a: Point, b: Point) -> int:
        """Return the traversal cost of the edge ``a``-``b``.

        Edges that run along a street are cheap; edges that cut through a
        cell interior are more expensive, which prioritises streets.
        """
        if a[0] == b[0]:
            return STREET_COST if a[0] % self.cell_size == 0 else CROSS_COST
        return STREET_COST if a[1] % self.cell_size == 0 else CROSS_COST

    def _node_path(self, start: Point, goal: Point) -> List[Point]:
        """Run Dijkstra over the search graph and return the node sequence."""
        if start == goal:
            return [start]
        distance = {start: 0}
        previous = {}
        heap = [(0, start)]
        while heap:
            cost, node = heapq.heappop(heap)
            if node == goal:
                break
            if cost > distance.get(node, math.inf):
                continue
            for neighbor in self._neighbors(node):
                new_cost = cost + self._edge_cost(node, neighbor)
                if new_cost < distance.get(neighbor, math.inf):
                    distance[neighbor] = new_cost
                    previous[neighbor] = node
                    heapq.heappush(heap, (new_cost, neighbor))
        if goal not in distance:
            return [start, goal]
        path = [goal]
        while path[-1] != start:
            path.append(previous[path[-1]])
        path.reverse()
        return path

    def plan(self, start: Sequence[int], target: Sequence[int]) -> List[Point]:
        """Plan an axis-aligned route from ``start`` to ``target``.

        The route is a list of waypoints that excludes ``start`` and ends at
        ``target``. An empty list means the rider is already at the target.
        Off-street starting points are connected to the street network with
        a short straight connector, which is the "special location" case.

        Args:
            start: Current position of the rider.
            target: Destination point.

        Returns:
            Ordered list of waypoints ``[(x, y), ...]``.
        """
        origin = (int(start[0]), int(start[1]))
        destination = (int(target[0]), int(target[1]))
        if origin == destination:
            return []

        begin = self.snap_to_node(origin)
        end = self.snap_to_node(destination)
        nodes = self._node_path(begin, end)

        raw = [origin] + nodes + [destination]
        deduped: List[Point] = []
        for point in raw:
            if not deduped or deduped[-1] != point:
                deduped.append(point)
        if len(deduped) < 2:
            return []

        waypoints: List[Point] = []
        previous = deduped[0]
        for point in deduped[1:]:
            if point[0] != previous[0] and point[1] != previous[1]:
                # Right-angle turn: move horizontally first, then vertically.
                waypoints.append((point[0], previous[1]))
            if not waypoints or waypoints[-1] != point:
                waypoints.append(point)
            previous = point
        return waypoints

    def plan_multi(self, start: Sequence[int], stops: Sequence[Sequence[int]]) -> List[Point]:
        """Plan a continuous route through several stops in order.

        Used for the pickup-to-delivery route so that the whole trip is one
        waypoint sequence.

        Args:
            start: Starting position.
            stops: Ordered destinations, e.g. ``[restaurant, customer]``.

        Returns:
            Concatenated waypoints excluding the start position.
        """
        route: List[Point] = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            leg = self.plan(current, stop)
            route.extend(leg)
            current = (int(stop[0]), int(stop[1]))
        return route
