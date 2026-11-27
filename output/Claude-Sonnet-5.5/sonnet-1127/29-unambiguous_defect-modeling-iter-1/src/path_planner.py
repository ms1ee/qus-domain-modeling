"""Grid based path planning."""
from grid_map import GridMap


class Path:
    """A path of waypoints."""

    def __init__(self, waypoints, speed=1):
        self.waypoints = waypoints
        self.total_distance = sum(
            abs(a[0] - b[0]) + abs(a[1] - b[1])
            for a, b in zip(waypoints, waypoints[1:]))
        self.estimated_time = -(-self.total_distance // max(1, speed))


class PathPlanner:
    """Plans right-angle paths (horizontal first, then vertical)."""

    def __init__(self, grid=None):
        self.grid = grid or GridMap()

    def plan(self, start, targets, speed=1):
        """Plan a path from start through each target in order."""
        pts = [tuple(start)]
        for t in targets:
            t = tuple(t)
            cur = pts[-1]
            if cur[0] != t[0] and cur[1] != t[1]:
                pts.append((t[0], cur[1]))
            if pts[-1] != t:
                pts.append(t)
        return Path(pts, speed)
