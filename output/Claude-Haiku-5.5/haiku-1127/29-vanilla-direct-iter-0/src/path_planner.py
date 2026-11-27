"""Grid-based path planning for riders.

Routes are axis-aligned polylines. Between a start and a goal the planner
chooses one of the two L-shaped routes, preferring the one whose legs run
along streets (grid lines at multiples of 100). Points that share an x or y
coordinate with the goal are reached by a straight line (the "directly
above or below" special case).
"""

from grid import CELL_SIZE


class PathPlanner:
    """Plans street-preferring, right-angle routes on the 800x800 map."""

    def plan(self, start, goal) -> list:
        """Compute the waypoints from start to goal.

        Args:
            start: Tuple (x, y) of the current position.
            goal: Tuple (x, y) of the destination.

        Returns:
            List of waypoints (tuples) ending at goal. Empty if the start
            already equals the goal. Consecutive points are axis-aligned.
        """
        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            # Directly above/below or beside the target: straight line.
            return [(gx, gy)]

        horizontal_first = (gx, sy)
        vertical_first = (sx, gy)
        h_score = (1 if sy % CELL_SIZE == 0 else 0) + \
                  (1 if gx % CELL_SIZE == 0 else 0)
        v_score = (1 if sx % CELL_SIZE == 0 else 0) + \
                  (1 if gy % CELL_SIZE == 0 else 0)
        corner = horizontal_first if h_score >= v_score else vertical_first
        return [corner, (gx, gy)]


def path_length(start, path) -> int:
    """Return the Manhattan length of a waypoint path starting at start."""
    total = 0
    cur = (int(start[0]), int(start[1]))
    for point in path:
        total += abs(point[0] - cur[0]) + abs(point[1] - cur[1])
        cur = point
    return total
