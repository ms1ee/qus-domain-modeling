"""Grid-based path planning for the 8x8 dispatch map.

The map is an 800x800 coordinate system divided into 100x100 cells.
Streets run along grid lines (x or y that is a multiple of the cell size).
The planner prefers L-shaped routes whose segments lie on streets and
produces axis-aligned waypoints only, so movement is always horizontal or
vertical (right-angle turns).
"""

import logging
import math

from config import CONFIG

logger = logging.getLogger("dispatch")


class Route:
    """Planned route made of axis-aligned waypoints.

    Attributes:
        waypoints: List of (x, y) points to visit in order (start excluded).
        total_distance: Manhattan length of the route in units.
        estimated_ticks: Number of ticks needed at the planning speed.
    """

    def __init__(self, waypoints=None, total_distance=0, estimated_ticks=0):
        self.waypoints = list(waypoints or [])
        self.total_distance = int(total_distance)
        self.estimated_ticks = int(estimated_ticks)


class PathPlanner:
    """Computes routes between two points on the grid.

    Attributes:
        prefer_streets: When True, the corner that keeps the most segments
            on streets is chosen.
    """

    def __init__(self, prefer_streets=True):
        """Create a planner.

        Args:
            prefer_streets: Whether street-aligned routes are preferred.
        """
        self.prefer_streets = prefer_streets

    @staticmethod
    def grid_center(value):
        """Convert a raw coordinate into the centre of its grid cell.

        Values outside the map are clamped to the map boundary.

        Args:
            value: Integer coordinate (0..map_size).

        Returns:
            ``(value // cell) * cell + cell // 2`` after clamping.
        """
        cell = CONFIG["cell_size"]
        limit = CONFIG["map_size"] - 1
        clamped = min(max(int(value), 0), limit)
        return (clamped // cell) * cell + cell // 2

    @staticmethod
    def is_street_segment(start, end):
        """Return True when an axis-aligned segment lies on a street.

        Args:
            start: (x, y) start point.
            end: (x, y) end point.

        Returns:
            True if the segment runs along a grid line.
        """
        cell = CONFIG["cell_size"]
        sx, sy = start
        ex, ey = end
        if sy == ey:
            return sy % cell == 0
        if sx == ex:
            return sx % cell == 0
        return False

    @staticmethod
    def path_length(start, waypoints):
        """Compute the Manhattan length of a polyline.

        Args:
            start: (x, y) starting point.
            waypoints: Sequence of (x, y) points.

        Returns:
            Total length in units.
        """
        total = 0
        current = start
        for point in waypoints:
            total += abs(point[0] - current[0]) + abs(point[1] - current[1])
            current = point
        return total

    def _off_street_count(self, start, waypoints):
        """Count segments of a candidate route that do not lie on streets."""
        count = 0
        current = start
        for point in waypoints:
            if not self.is_street_segment(current, point):
                count += 1
            current = point
        return count

    @staticmethod
    def _candidate_paths(start, goal):
        """Generate candidate waypoint lists for the route start -> goal."""
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [[goal]]
        # Horizontal-first corner and vertical-first corner.
        return [[(gx, sy), goal], [(sx, gy), goal]]

    def plan(self, start, goal, speed=1):
        """Plan a right-angle route from ``start`` to ``goal``.

        Special case: when the goal is directly above/below or beside the
        start, a single straight segment is used.

        Args:
            start: (x, y) current position.
            goal: (x, y) destination.
            speed: Units per tick used to estimate travel time.

        Returns:
            A Route whose waypoints exclude the start point.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return Route([], 0, 0)

        candidates = self._candidate_paths(start, goal)
        if self.prefer_streets and len(candidates) > 1:
            best = min(candidates, key=lambda path: self._off_street_count(start, path))
        else:
            best = candidates[0]

        total = self.path_length(start, best)
        speed = max(1, int(speed))
        estimated = math.ceil(total / speed)
        logger.debug("Planned route %s -> %s: %s", start, goal, best)
        return Route(best, total, estimated)
