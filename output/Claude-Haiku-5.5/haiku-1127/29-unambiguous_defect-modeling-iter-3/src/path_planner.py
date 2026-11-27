"""Grid-based path planning restricted to the street network."""

from collections import deque

from grid import is_road

_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class PathPlanner:
    """Computes unit-step routes along streets between two points.

    Routes only pass through road points (x or y on a 100-unit grid line),
    so movement always follows streets and turns at right angles. When the
    start and goal are directly above or below each other (or left or right),
    a straight-line fast path is tried first.
    """

    def __init__(self, prefer_streets=True):
        """Create a planner.

        Args:
            prefer_streets: When True, the straight fast path is tried before
                the general search. Routes always stay on streets either way.
        """
        self.prefer_streets = prefer_streets

    def plan(self, start, goal):
        """Compute a street route from ``start`` to ``goal``.

        Args:
            start: Tuple (x, y) of the origin, which must be on a road.
            goal: Tuple (x, y) of the destination, which must be on a road.

        Returns:
            list[tuple[int, int]]: Unit-step points from ``start`` (exclusive)
            to ``goal`` (inclusive). Empty if the two points are equal.

        Raises:
            ValueError: If either point is not on a road.
            RuntimeError: If no route exists.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if not is_road(*start) or not is_road(*goal):
            raise ValueError("Route endpoints must lie on a street: %r -> %r" % (start, goal))

        aligned = start[0] == goal[0] or start[1] == goal[1]
        if self.prefer_streets and aligned:
            straight = self._straight(start, goal)
            if straight is not None:
                return straight
        return self._search(start, goal)

    @staticmethod
    def _straight(start, goal):
        """Return a straight unit-step path if every point on it is a road.

        Args:
            start: Origin point.
            goal: Destination point, aligned with ``start`` on one axis.

        Returns:
            list of points, or None if the straight line leaves the streets.
        """
        sx, sy = start
        gx, gy = goal
        if sx == gx:
            step = 1 if gy > sy else -1
            points = [(sx, y) for y in range(sy + step, gy + step, step)]
        else:
            step = 1 if gx > sx else -1
            points = [(x, sy) for x in range(sx + step, gx + step, step)]
        if all(is_road(x, y) for x, y in points):
            return points
        return None

    @staticmethod
    def _search(start, goal):
        """Breadth-first search over street points.

        Args:
            start: Origin point.
            goal: Destination point.

        Returns:
            list of points from start (exclusive) to goal (inclusive).

        Raises:
            RuntimeError: If the goal cannot be reached.
        """
        parent = {start: None}
        queue = deque([start])
        found = False
        while queue:
            current = queue.popleft()
            if current == goal:
                found = True
                break
            for dx, dy in _STEPS:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt in parent or not is_road(*nxt):
                    continue
                parent[nxt] = current
                queue.append(nxt)
        if not found:
            raise RuntimeError("No street route from %r to %r" % (start, goal))

        path = []
        node = goal
        while node != start:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    @staticmethod
    def path_length(path):
        """Return the number of unit steps in a planned path.

        Args:
            path: List of points as returned by ``plan``.

        Returns:
            int: Number of steps.
        """
        return len(path)
