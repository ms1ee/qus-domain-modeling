"""Grid-based path planning for riders.

The planner works on a lattice with a 50-unit step. Lattice points whose
coordinates are both multiples of 100 or where exactly one coordinate is a
multiple of 100 are street points. Points where both coordinates are odd
multiples of 50 are cell-centre locations (restaurants and customers).
Locations are only allowed as route endpoints, so routes always follow
streets between them.
"""

import heapq
import logging
import random

import config

logger = logging.getLogger(__name__)

STEP_COST = 1
OCCUPIED_PENALTY = 2
_INF = float("inf")


class PathPlanner:
    """Compute axis-aligned routes along the street grid."""

    @staticmethod
    def is_location(point):
        """Return True if the point is a cell-centre location.

        Args:
            point: ``(x, y)`` tuple.

        Returns:
            True when both coordinates are at cell centres.
        """
        half = config.CELL_SIZE // 2
        x, y = point
        return x % config.CELL_SIZE == half and y % config.CELL_SIZE == half

    @staticmethod
    def is_street(point):
        """Return True if the point lies on a street grid line.

        Args:
            point: ``(x, y)`` tuple.

        Returns:
            True when ``x`` or ``y`` is a multiple of the cell size.
        """
        x, y = point
        return x % config.CELL_SIZE == 0 or y % config.CELL_SIZE == 0

    @staticmethod
    def snap(point):
        """Snap an arbitrary point to the nearest lattice point inside the map.

        Args:
            point: ``(x, y)`` tuple of numbers.

        Returns:
            ``(x, y)`` tuple of integers on the lattice.
        """
        step = config.LATTICE_STEP
        limit = config.MAP_SIZE

        def _snap(value):
            snapped = int(round(value / step)) * step
            return min(max(snapped, 0), limit)

        return _snap(point[0]), _snap(point[1])

    @staticmethod
    def lattice_points():
        """Return every lattice point on the map.

        Returns:
            List of ``(x, y)`` tuples.
        """
        step = config.LATTICE_STEP
        return [
            (x, y)
            for x in range(0, config.MAP_SIZE + 1, step)
            for y in range(0, config.MAP_SIZE + 1, step)
        ]

    @staticmethod
    def neighbors(point):
        """Return the four axis-aligned neighbours of a lattice point.

        Args:
            point: ``(x, y)`` lattice tuple.

        Returns:
            List of neighbouring points that lie inside the map.
        """
        step = config.LATTICE_STEP
        x, y = point
        candidates = [(x + step, y), (x - step, y), (x, y + step), (x, y - step)]
        return [
            (nx, ny)
            for nx, ny in candidates
            if 0 <= nx <= config.MAP_SIZE and 0 <= ny <= config.MAP_SIZE
        ]

    @staticmethod
    def manhattan(a, b):
        """Return the Manhattan distance between two points.

        Args:
            a: First ``(x, y)`` point.
            b: Second ``(x, y)`` point.

        Returns:
            Integer distance in map units.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def path_length(path):
        """Return the length in map units of a path.

        Args:
            path: List of lattice points, including the start point.

        Returns:
            Total length in units.
        """
        if not path:
            return 0
        return max(len(path) - 1, 0) * config.LATTICE_STEP

    @staticmethod
    def street_points():
        """Return all lattice points lying on streets.

        Returns:
            List of street ``(x, y)`` tuples.
        """
        return [p for p in PathPlanner.lattice_points() if PathPlanner.is_street(p)]

    @classmethod
    def random_street_point(cls, rng=None):
        """Pick a random street point, used for initial rider placement.

        Args:
            rng: Optional random number generator object.

        Returns:
            A random street ``(x, y)`` tuple.
        """
        rng = rng or random
        return rng.choice(_STREET_POINTS)

    @classmethod
    def straight_path(cls, start, goal):
        """Special case: rider and target are directly above or below each other.

        When the start and goal share an x or y coordinate and every
        intermediate point lies on a street, the straight segment is used.

        Args:
            start: Start lattice point.
            goal: Goal lattice point.

        Returns:
            Path list including start and goal, or None if not applicable.
        """
        step = config.LATTICE_STEP
        if start[0] == goal[0]:
            direction = (0, step if goal[1] > start[1] else -step)
        elif start[1] == goal[1]:
            direction = (step if goal[0] > start[0] else -step, 0)
        else:
            return None
        path = [start]
        current = start
        while current != goal:
            current = (current[0] + direction[0], current[1] + direction[1])
            if current != goal and not cls.is_street(current):
                return None
            path.append(current)
        return path

    @classmethod
    def plan(cls, start, goal, occupied=None):
        """Plan a street-following route from start to goal.

        Uses Dijkstra's algorithm on the lattice. Cell-centre locations are
        only entered when they are the goal, which keeps routes on streets.
        Points occupied by other riders carry a small extra cost, which
        steers riders apart and reduces path conflicts.

        Args:
            start: Start ``(x, y)`` point.
            goal: Goal ``(x, y)`` point.
            occupied: Optional collection of points occupied by other riders.

        Returns:
            List of lattice points from start to goal (both included).
        """
        start = cls.snap(start)
        goal = cls.snap(goal)
        if start == goal:
            return [start]
        straight = cls.straight_path(start, goal)
        if straight is not None:
            return straight

        occupied = set(occupied or ())
        dist = {start: 0}
        prev = {}
        heap = [(0, start)]
        while heap:
            cost, node = heapq.heappop(heap)
            if node == goal:
                break
            if cost > dist.get(node, _INF):
                continue
            for neighbor in cls.neighbors(node):
                if neighbor != goal and not cls.is_street(neighbor):
                    continue
                step_cost = STEP_COST
                if neighbor in occupied:
                    step_cost += OCCUPIED_PENALTY
                new_cost = cost + step_cost
                if new_cost < dist.get(neighbor, _INF):
                    dist[neighbor] = new_cost
                    prev[neighbor] = node
                    heapq.heappush(heap, (new_cost, neighbor))

        if goal not in dist:
            logger.warning("No route from %s to %s; staying in place", start, goal)
            return [start]
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path


_STREET_POINTS = tuple(PathPlanner.street_points())
