"""Grid-based path planning for the simulated 800x800 map.

The map is an 8x8 grid of 100x100 cells. Streets run along the grid lines
(coordinates that are multiples of 100). Intersections are the points where
two streets meet; restaurants and customers are attached to intersections.
Routes are computed on the intersection graph and prefer straight segments
over turns (right-angle turns are allowed but penalised).
"""

import heapq
import itertools
import logging
import math
import random
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
NODE_COUNT = GRID_SIZE + 1  # 9 intersections per axis

Point = Tuple[int, int]

# Direction indices: 0=east, 1=west, 2=north, 3=south.
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))
TURN_PENALTY = 0.5
_INF = float("inf")


class PathPlanner:
    """Stateless helper providing coordinate conversion and route planning."""

    # ------------------------------------------------------------------ #
    # Coordinate helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def clamp_coordinate(value: int) -> int:
        """Clamp a coordinate into the map range ``[0, MAP_SIZE]``."""
        return max(0, min(MAP_SIZE, int(value)))

    @staticmethod
    def snap_to_road(value: int) -> int:
        """Round a coordinate to the nearest grid line (a multiple of 100).

        Half values round upwards, and the result is clamped to the map.

        Args:
            value: Raw coordinate in the range 0-800.

        Returns:
            The nearest multiple of ``CELL_SIZE`` within the map.
        """
        snapped = math.floor(int(value) / CELL_SIZE + 0.5) * CELL_SIZE
        return max(0, min(MAP_SIZE, snapped))

    @staticmethod
    def cell_index(value: int) -> int:
        """Return the grid cell index (0-7) containing ``value``."""
        return min(max(int(value), 0) // CELL_SIZE, GRID_SIZE - 1)

    @classmethod
    def grid_center(cls, value: int) -> int:
        """Return the centre coordinate of the cell containing ``value``.

        Implements ``center = (grid // 100) * 100 + 50``.
        """
        return cls.cell_index(value) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def is_intersection(x: int, y: int) -> bool:
        """Return True if the point lies on a street intersection."""
        return (
            0 <= x <= MAP_SIZE
            and 0 <= y <= MAP_SIZE
            and x % CELL_SIZE == 0
            and y % CELL_SIZE == 0
        )

    @staticmethod
    def is_on_road(x: int, y: int) -> bool:
        """Return True if the point lies on any street (grid line)."""
        return (
            0 <= x <= MAP_SIZE
            and 0 <= y <= MAP_SIZE
            and (x % CELL_SIZE == 0 or y % CELL_SIZE == 0)
        )

    @staticmethod
    def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
        """Return the Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def is_aligned(a: Sequence[int], b: Sequence[int]) -> bool:
        """Return True if ``b`` is directly above/below or beside ``a``.

        This is the "special case" in which a straight-line movement along a
        single street reaches the target without any turn.
        """
        return (a[0] == b[0] or a[1] == b[1]) and tuple(a) != tuple(b)

    @staticmethod
    def random_node(rng: Optional[random.Random] = None) -> Point:
        """Return a random street intersection (used to place riders)."""
        source = rng or random
        return (
            source.randrange(NODE_COUNT) * CELL_SIZE,
            source.randrange(NODE_COUNT) * CELL_SIZE,
        )

    @staticmethod
    def route_length(points: Sequence[Point]) -> int:
        """Return the total Manhattan length of a polyline of points."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return total

    # ------------------------------------------------------------------ #
    # Route planning
    # ------------------------------------------------------------------ #
    @classmethod
    def plan(cls, start: Point, goal: Point) -> List[Point]:
        """Plan a street route between two intersections.

        Uses Dijkstra's algorithm over ``(intersection, heading)`` states so
        that straight-line movement is preferred and right-angle turns are
        only taken when they shorten the route.

        Args:
            start: Starting intersection (both coordinates multiples of 100).
            goal: Destination intersection.

        Returns:
            Ordered list of intersections visited after ``start``, ending with
            ``goal``. Empty if ``start == goal``.

        Raises:
            ValueError: If either endpoint is not an intersection.
            RuntimeError: If no route exists (should not happen on the grid).
        """
        if not cls.is_intersection(*start) or not cls.is_intersection(*goal):
            raise ValueError(f"route endpoints must be intersections: {start} -> {goal}")
        if tuple(start) == tuple(goal):
            return []

        origin = (start[0] // CELL_SIZE, start[1] // CELL_SIZE)
        target = (goal[0] // CELL_SIZE, goal[1] // CELL_SIZE)
        origin_state = (origin, -1)

        dist = {origin_state: 0.0}
        prev = {}
        counter = itertools.count()
        heap = [(0.0, next(counter), origin_state)]
        found = None

        while heap:
            cost, _, state = heapq.heappop(heap)
            if cost > dist.get(state, _INF):
                continue
            node, last_dir = state
            if node == target:
                found = state
                break
            for idx, (dx, dy) in enumerate(DIRECTIONS):
                nx, ny = node[0] + dx, node[1] + dy
                if not (0 <= nx < NODE_COUNT and 0 <= ny < NODE_COUNT):
                    continue
                step = 1.0
                if last_dir != -1 and idx != last_dir:
                    step += TURN_PENALTY
                nxt = ((nx, ny), idx)
                new_cost = cost + step
                if new_cost < dist.get(nxt, _INF):
                    dist[nxt] = new_cost
                    prev[nxt] = state
                    heapq.heappush(heap, (new_cost, next(counter), nxt))

        if found is None:
            raise RuntimeError(f"no route found from {start} to {goal}")

        nodes = []
        state = found
        while state != origin_state:
            nodes.append(state[0])
            state = prev[state]
        nodes.reverse()
        return [(x * CELL_SIZE, y * CELL_SIZE) for x, y in nodes]

    @staticmethod
    def _street_endpoints(pos: Point) -> List[Point]:
        """Return the intersections bounding the street segment holding ``pos``."""
        x, y = pos
        if x % CELL_SIZE == 0:
            lo = (y // CELL_SIZE) * CELL_SIZE
            candidates = [(x, lo), (x, lo + CELL_SIZE)]
        else:
            lo = (x // CELL_SIZE) * CELL_SIZE
            candidates = [(lo, y), (lo + CELL_SIZE, y)]
        return [
            c for c in candidates if 0 <= c[0] <= MAP_SIZE and 0 <= c[1] <= MAP_SIZE
        ]

    @classmethod
    def route_from(cls, pos: Point, target: Point) -> List[Point]:
        """Plan a route from any road point (possibly mid-street) to ``target``.

        If ``pos`` is mid-street, the route first leaves through the segment
        endpoint that gives the shortest total distance to ``target``.

        Returns:
            Ordered list of points after ``pos`` ending with ``target``.
        """
        if cls.is_intersection(*pos):
            return cls.plan(pos, target)
        best = min(
            cls._street_endpoints(pos),
            key=lambda e: cls.manhattan(pos, e) + cls.manhattan(e, target),
        )
        return [best] + cls.plan(best, target)

    @classmethod
    def full_route(cls, pos: Point, restaurant: Point, customer: Point) -> List[Point]:
        """Return the continuous route pos -> restaurant -> customer.

        The result starts with ``pos`` itself and is used for route display
        and time estimation.
        """
        route = [tuple(pos)]
        route.extend(cls.route_from(tuple(pos), tuple(restaurant)))
        route.extend(cls.plan(tuple(restaurant), tuple(customer)))
        return route
