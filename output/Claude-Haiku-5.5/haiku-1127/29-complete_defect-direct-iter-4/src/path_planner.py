"""Grid-based path planning that prefers streets.

The city is an 800x800 unit map split into 8x8 cells of 100x100 units.
Streets run along the grid lines (x or y multiple of 100). Locations are
cell centers (50 + 100*k). A route leaves a location through its own cell
to a street corner, travels along streets (Dijkstra over the 9x9 lattice of
intersections) and enters the destination cell the same way.
"""

import heapq
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

Point = Tuple[int, int]

GRID_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = GRID_SIZE // CELL_SIZE
_INF = float("inf")


def cell_center(value: int) -> int:
    """Convert a coordinate into the center of its grid cell.

    Implements ``center = (value // 100) * 100 + 50`` with the index clamped
    to the valid range so that the boundary value 800 maps to the last cell.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        The center coordinate of the containing cell.
    """
    index = min(max(int(value) // CELL_SIZE, 0), GRID_CELLS - 1)
    return index * CELL_SIZE + CELL_SIZE // 2


def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point (x, y).
        b: Second point (x, y).

    Returns:
        The sum of absolute coordinate differences.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def grid_cell(point: Sequence[int]) -> Point:
    """Return the zero-based grid cell (column, row) containing a point.

    Args:
        point: Coordinates (x, y).

    Returns:
        Tuple (column, row), each in 0..7.
    """
    col = min(point[0] // CELL_SIZE, GRID_CELLS - 1)
    row = min(point[1] // CELL_SIZE, GRID_CELLS - 1)
    return (col, row)


def _axis_candidates(value: int) -> List[int]:
    """Return the street lines reachable from a coordinate along one axis."""
    if value % CELL_SIZE == 0:
        return [value]
    base = (value // CELL_SIZE) * CELL_SIZE
    return [base, base + CELL_SIZE]


def _lattice_neighbors(node: Point) -> Iterator[Point]:
    """Yield the adjacent street intersections of a lattice node."""
    x, y = node
    for dx, dy in ((CELL_SIZE, 0), (-CELL_SIZE, 0), (0, CELL_SIZE), (0, -CELL_SIZE)):
        nx, ny = x + dx, y + dy
        if 0 <= nx <= GRID_SIZE and 0 <= ny <= GRID_SIZE:
            yield (nx, ny)


class PathPlanner:
    """Plans axis-aligned routes that follow streets."""

    def plan(self, start: Sequence[int], goal: Sequence[int]) -> List[Point]:
        """Compute a street-following route from ``start`` to ``goal``.

        The first element of the returned list is always ``start`` and the
        last element is always ``goal``. Consecutive points are axis aligned.

        Args:
            start: Current position (x, y).
            goal: Destination position (x, y).

        Returns:
            List of waypoints including start and goal.
        """
        start_pt: Point = (int(start[0]), int(start[1]))
        goal_pt: Point = (int(goal[0]), int(goal[1]))
        if start_pt == goal_pt:
            return [start_pt]

        start_access = self._access_paths(start_pt)
        goal_access = self._access_paths(goal_pt)

        dist: Dict[Point, float] = {}
        prev: Dict[Point, Optional[Point]] = {}
        start_paths: Dict[Point, List[Point]] = {}
        heap: List[Tuple[float, Point]] = []
        for corner, pts, cost in start_access:
            if cost < dist.get(corner, _INF):
                dist[corner] = cost
                prev[corner] = None
                start_paths[corner] = pts
                heapq.heappush(heap, (cost, corner))

        while heap:
            cur_dist, node = heapq.heappop(heap)
            if cur_dist > dist.get(node, _INF):
                continue
            for neighbor in _lattice_neighbors(node):
                new_dist = cur_dist + CELL_SIZE
                if new_dist < dist.get(neighbor, _INF):
                    dist[neighbor] = new_dist
                    prev[neighbor] = node
                    heapq.heappush(heap, (new_dist, neighbor))

        best: Optional[Tuple[float, Point, List[Point]]] = None
        for corner, pts, cost in goal_access:
            if corner in dist:
                total = dist[corner] + cost
                if best is None or total < best[0]:
                    best = (total, corner, pts)
        if best is None:  # pragma: no cover - lattice is always connected
            raise RuntimeError(f"No route found from {start_pt} to {goal_pt}")

        _, goal_corner, goal_pts = best
        nodes: List[Point] = []
        node: Optional[Point] = goal_corner
        while node is not None:
            nodes.append(node)
            node = prev[node]
        nodes.reverse()

        path = list(start_paths[nodes[0]]) + nodes[1:] + list(reversed(goal_pts))[1:]
        return self._dedupe(path)

    def _access_paths(self, point: Point) -> List[Tuple[Point, List[Point], int]]:
        """Return the ways to reach a street corner from ``point``.

        Each entry is (corner, waypoints_to_corner, cost). The waypoints
        travel horizontally to the street line first, then vertically.
        """
        x, y = point
        results = []
        for sx in _axis_candidates(x):
            for sy in _axis_candidates(y):
                pts = self._dedupe([point, (sx, y), (sx, sy)])
                results.append(((sx, sy), pts, manhattan(point, (sx, sy))))
        return results

    @staticmethod
    def _dedupe(points: Sequence[Point]) -> List[Point]:
        """Remove consecutive duplicate waypoints."""
        result: List[Point] = []
        for pt in points:
            if not result or result[-1] != pt:
                result.append((int(pt[0]), int(pt[1])))
        return result

    @staticmethod
    def route_length(points: Sequence[Point]) -> int:
        """Return the total travelled length of a waypoint list."""
        return sum(manhattan(a, b) for a, b in zip(points, points[1:]))

    @staticmethod
    def is_straight(points: Sequence[Point]) -> bool:
        """Return True if all waypoints lie on one vertical or horizontal line.

        This identifies the special case where the target is directly above,
        below, left or right of the rider.
        """
        if len(points) <= 1:
            return True
        return len({p[0] for p in points}) == 1 or len({p[1] for p in points}) == 1
