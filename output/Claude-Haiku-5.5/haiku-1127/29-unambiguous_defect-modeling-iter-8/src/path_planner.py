"""Grid-based path planning for riders.

Riders travel along the street network. A Dijkstra search on the 50-unit
lattice minimises the number of steps first and the number of right-angle
turns second, which prioritises straight streets. Location points (cell
centres) can only be used as the start or goal of a path, so riders never
cut through a block.
"""

import heapq
import random
from typing import List, Optional, Sequence, Tuple

from grid_map import LATTICE_STEP, GridMap, Point

DIRECTIONS = (
    (LATTICE_STEP, 0),
    (-LATTICE_STEP, 0),
    (0, LATTICE_STEP),
    (0, -LATTICE_STEP),
)
NO_DIRECTION = (0, 0)
STEP_COST = 10
TURN_COST = 1


class PathPlanner:
    """Plan grid-based routes between points on the map."""

    def __init__(self, grid: Optional[GridMap] = None) -> None:
        """Create a planner for the given grid.

        Args:
            grid: Grid map to plan on. A default 8x8 map is created if None.
        """
        self.grid = grid if grid is not None else GridMap()
        self._street_points: List[Point] = [
            p for p in self.grid.lattice_points() if self.grid.is_street(*p)
        ]

    @property
    def street_points(self) -> List[Point]:
        """Return a copy of all street lattice points.

        Returns:
            List of street points.
        """
        return list(self._street_points)

    def _passable(self, point: Point, goal: Point) -> bool:
        """Return True if a point may be entered during the search.

        Args:
            point: Candidate point.
            goal: Destination of the current search.

        Returns:
            True for street points and for the goal itself.
        """
        return self.grid.is_street(point[0], point[1]) or point == goal

    def find_path(self, start: Point, goal: Point) -> List[Point]:
        """Find a street-following path from start to goal.

        The returned list starts with ``start`` and ends with ``goal``. An
        empty list is returned when no path exists.

        Args:
            start: Starting lattice point.
            goal: Destination lattice point.

        Returns:
            Ordered list of lattice points forming the path.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]

        start_state = (start, NO_DIRECTION)
        best = {start_state: 0}
        prev = {}
        heap = [(0, start, NO_DIRECTION)]
        end_state = None

        while heap:
            cost, current, direction = heapq.heappop(heap)
            state = (current, direction)
            if cost > best.get(state, float("inf")):
                continue
            if current == goal:
                end_state = state
                break
            for nd in DIRECTIONS:
                nxt = (current[0] + nd[0], current[1] + nd[1])
                if not self._passable(nxt, goal):
                    continue
                step = STEP_COST
                if direction != NO_DIRECTION and nd != direction:
                    step += TURN_COST
                new_cost = cost + step
                key = (nxt, nd)
                if new_cost < best.get(key, float("inf")):
                    best[key] = new_cost
                    prev[key] = state
                    heapq.heappush(heap, (new_cost, nxt, nd))

        if end_state is None:
            return []

        path: List[Point] = []
        state = end_state
        while True:
            path.append(state[0])
            if state == start_state:
                break
            state = prev[state]
        path.reverse()
        return path

    def plan_route(self, points: Sequence[Point]) -> List[Point]:
        """Plan a continuous route through several destinations in order.

        Args:
            points: Ordered list of waypoints, e.g. rider, restaurant, customer.

        Returns:
            Concatenated lattice path visiting every waypoint in order.
        """
        route: List[Point] = []
        for a, b in zip(points, points[1:]):
            segment = self.find_path(a, b) or [a, b]
            if not route:
                route.extend(segment)
            else:
                route.extend(segment[1:])
        if not route and points:
            route = [points[0]]
        return route

    @staticmethod
    def path_length(path: Sequence[Point]) -> int:
        """Return the length of a path in map units.

        Args:
            path: Ordered list of lattice points.

        Returns:
            Number of steps multiplied by the lattice step size.
        """
        return max(0, len(path) - 1) * LATTICE_STEP

    def random_road_point(self) -> Point:
        """Return a random street point for placing a rider.

        Returns:
            A street lattice point.
        """
        return random.choice(self._street_points)

    def straight_line_ok(self, start: Point, goal: Point) -> bool:
        """Return True when start and goal share a row or column.

        Such targets are reached by a straight run, the special case of a
        rider directly above or below its target.

        Args:
            start: Starting point.
            goal: Destination point.

        Returns:
            True if the two points are vertically or horizontally aligned.
        """
        return start[0] == goal[0] or start[1] == goal[1]
