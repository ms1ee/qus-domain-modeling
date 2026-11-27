"""Grid-based path planning for riders moving along the street network.

Streets run through the cell centers: every intersection is a cell center
(x and y each equal 50 + 100k), and the streets connect neighbouring
intersections with horizontal and vertical straight segments. Routes are
therefore made of right-angle turns and straight-line movement only.
"""

import math

import grid


class PathPlanner:
    """Compute waypoint routes between street intersections."""

    @staticmethod
    def is_straight(start, goal):
        """Return True when the goal lies directly above, below, left or right.

        This is the special case of a target on the same vertical or
        horizontal street, which is traversed as a single straight line.

        Args:
            start: Current position (x, y).
            goal: Target position (x, y).

        Returns:
            bool: True if the move is a single straight segment.
        """
        return start[0] == goal[0] or start[1] == goal[1]

    @staticmethod
    def plan(start, goal, occupied=None):
        """Plan a street route from ``start`` to ``goal``.

        Two L-shaped routes exist (horizontal-first or vertical-first). The
        planner prefers the route whose corner intersection is not occupied by
        another rider, which avoids path conflicts. Straight-line cases return
        a single waypoint.

        Args:
            start: Starting position (x, y).
            goal: Destination position (x, y).
            occupied: Optional iterable of positions occupied by other riders.

        Returns:
            list[tuple[int, int]]: Waypoints after ``start``, ending at ``goal``.
            Empty if already at the goal.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [goal]

        occupied_set = set(occupied) if occupied else set()
        horizontal_first = (gx, sy)
        vertical_first = (sx, gy)
        if horizontal_first in occupied_set and vertical_first not in occupied_set:
            corner = vertical_first
        else:
            corner = horizontal_first
        return [corner, goal]

    @staticmethod
    def plan_multi(start, stops, occupied=None):
        """Plan a continuous route through several destinations in order.

        Args:
            start: Starting position (x, y).
            stops: Ordered destinations, e.g. [restaurant, customer].
            occupied: Optional iterable of positions occupied by other riders.

        Returns:
            list[tuple[int, int]]: Concatenated waypoints for the full route.
        """
        waypoints = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            waypoints.extend(PathPlanner.plan(current, stop, occupied))
            current = (int(stop[0]), int(stop[1]))
        return waypoints

    @staticmethod
    def path_length(start, waypoints):
        """Return the total street distance of a waypoint route.

        Args:
            start: Starting position (x, y).
            waypoints: Waypoints following the start position.

        Returns:
            int: Total travelled distance in units.
        """
        total = 0
        current = start
        for point in waypoints:
            total += grid.manhattan(current, point)
            current = point
        return total

    @staticmethod
    def estimate_ticks(start, stops, speed):
        """Estimate the number of ticks needed to visit all stops.

        Args:
            start: Starting position (x, y).
            stops: Ordered destinations.
            speed: Rider speed in units per tick.

        Returns:
            int: Estimated ticks (rounded up); 0 if speed is not positive.
        """
        if speed <= 0:
            return 0
        route = PathPlanner.plan_multi(start, stops)
        return math.ceil(PathPlanner.path_length(start, route) / speed)
