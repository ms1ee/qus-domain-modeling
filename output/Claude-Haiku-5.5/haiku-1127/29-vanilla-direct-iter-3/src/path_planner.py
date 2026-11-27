"""Grid-based path planning for the 800x800 street map.

The map is an 8x8 grid of 100x100 cells. Streets are the lines whose x or y
coordinate is a multiple of 100. Restaurant and customer locations are cell
centres (for example (150, 250)), which are not on a street; they are reached
through the street segment that bounds their cell.

Routes are sequences of axis-aligned segments, so every route can be driven
by a rider moving along horizontal or vertical lines only.
"""

import heapq
import math
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
HALF_CELL = 50


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_length(path: Sequence[Point]) -> int:
    """Return the total travelled length (along streets) of a polyline."""
    return sum(manhattan(path[i], path[i + 1]) for i in range(len(path) - 1))


def is_on_street(point: Point) -> bool:
    """Return True if the point lies on a street line."""
    return point[0] % CELL_SIZE == 0 or point[1] % CELL_SIZE == 0


def is_intersection(point: Point) -> bool:
    """Return True if the point is a street intersection."""
    return point[0] % CELL_SIZE == 0 and point[1] % CELL_SIZE == 0


def _in_map(point: Point) -> bool:
    """Return True if the point lies inside the map bounds."""
    return 0 <= point[0] <= MAP_SIZE and 0 <= point[1] <= MAP_SIZE


def _append(path: List[Point], point: Point) -> None:
    """Append ``point`` to ``path`` unless it duplicates the last point."""
    if not path or path[-1] != point:
        path.append(point)


def snap_to_street(point: Point) -> Point:
    """Return the nearest street point reachable by one axis-aligned move.

    Args:
        point: Any point inside the map.

    Returns:
        ``point`` itself when it is already on a street, otherwise the
        closest point on a street that shares either its x or y coordinate.
    """
    if is_on_street(point):
        return point
    x, y = point
    row_y = min(MAP_SIZE, (y + HALF_CELL) // CELL_SIZE * CELL_SIZE)
    col_x = min(MAP_SIZE, (x + HALF_CELL) // CELL_SIZE * CELL_SIZE)
    candidates = ((x, row_y), (col_x, y))
    return min(candidates, key=lambda q: manhattan(point, q))


class PathPlanner:
    """Plans street-following routes between arbitrary map points.

    The planner runs Dijkstra's algorithm over the 9x9 grid of street
    intersections. Off-street start and target points are connected to the
    intersections through the street segments that bound them. A target that
    lies directly above, below, left or right of a street segment is reached
    through the matching access point on that segment, which covers the
    "target directly above or below" special case.
    """

    def plan(self, start: Point, target: Point) -> List[Point]:
        """Compute a street-following route from ``start`` to ``target``.

        Args:
            start: Starting point (integer coordinates, 0-800).
            target: Destination point (integer coordinates, 0-800).

        Returns:
            Waypoint list beginning with ``start`` and ending with
            ``target``. Consecutive waypoints differ along one axis only.
        """
        start = (int(start[0]), int(start[1]))
        target = (int(target[0]), int(target[1]))
        if start == target:
            return [start]

        dist: Dict[Point, int] = {}
        prev: Dict[Point, Optional[Point]] = {}
        head: Dict[Point, List[Point]] = {}
        heap: List[Tuple[int, Point]] = []

        for node, poly in self._exits(start):
            cost = path_length(poly)
            if node not in dist or cost < dist[node]:
                dist[node] = cost
                prev[node] = None
                head[node] = poly
                heapq.heappush(heap, (cost, node))

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist.get(u, math.inf):
                continue
            for v in self._neighbours(u):
                nd = d + CELL_SIZE
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

        best: Optional[Tuple[int, Point, List[Point]]] = None
        for node, tail in self._entries(target):
            if node not in dist:
                continue
            total = dist[node] + path_length(tail)
            if best is None or total < best[0]:
                best = (total, node, tail)

        if best is None:
            return [start, target]

        _, node, tail = best
        chain: List[Point] = []
        cur: Optional[Point] = node
        while cur is not None:
            chain.append(cur)
            cur = prev.get(cur)
        chain.reverse()

        path = list(head[chain[0]])
        for step in chain[1:]:
            _append(path, step)
        for point in tail:
            _append(path, point)
        return path

    def plan_route(self, start: Point, restaurant: Point,
                   customer: Point) -> List[Point]:
        """Compute the continuous route start -> restaurant -> customer.

        Args:
            start: Rider's current position.
            restaurant: Pickup point (grid cell centre).
            customer: Delivery point (grid cell centre).

        Returns:
            Single waypoint list covering both legs without duplicates.
        """
        route = list(self.plan(start, restaurant))
        for point in self.plan(restaurant, customer):
            _append(route, point)
        return route

    def _exits(self, point: Point) -> List[Tuple[Point, List[Point]]]:
        """Return intersections reachable from ``point`` along streets.

        Each result is ``(node, poly)`` where ``poly`` starts at ``point``
        and ends at ``node``.
        """
        if is_intersection(point):
            return [(point, [point])]
        if is_on_street(point):
            x, y = point
            if x % CELL_SIZE == 0:
                nodes = [(x, (y // CELL_SIZE) * CELL_SIZE),
                         (x, ((y + CELL_SIZE - 1) // CELL_SIZE) * CELL_SIZE)]
            else:
                nodes = [((x // CELL_SIZE) * CELL_SIZE, y),
                         (((x + CELL_SIZE - 1) // CELL_SIZE) * CELL_SIZE, y)]
            result: List[Tuple[Point, List[Point]]] = []
            seen = set()
            for node in nodes:
                if node in seen or not _in_map(node):
                    continue
                seen.add(node)
                result.append((node, [point, node]))
            return result
        snapped = snap_to_street(point)
        return [(node, [point] + poly)
                for node, poly in self._exits(snapped)]

    def _entries(self, target: Point) -> List[Tuple[Point, List[Point]]]:
        """Return intersections from which ``target`` can be reached.

        Each result is ``(node, tail)`` where ``tail`` starts at ``node``
        and ends at ``target``.
        """
        if is_on_street(target):
            return [(node, list(reversed(poly)))
                    for node, poly in self._exits(target)]
        x, y = target
        entries: List[Tuple[Point, List[Point]]] = []
        access_points = ((x - HALF_CELL, y), (x + HALF_CELL, y),
                         (x, y - HALF_CELL), (x, y + HALF_CELL))
        for access in access_points:
            if not _in_map(access) or not is_on_street(access):
                continue
            for node, poly in self._exits(access):
                entries.append((node, list(reversed(poly)) + [target]))
        return entries

    @staticmethod
    def _neighbours(node: Point) -> List[Point]:
        """Return the adjacent intersections of ``node`` inside the map."""
        x, y = node
        candidates = ((x + CELL_SIZE, y), (x - CELL_SIZE, y),
                      (x, y + CELL_SIZE), (x, y - CELL_SIZE))
        return [p for p in candidates if _in_map(p)]
