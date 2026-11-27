"""Grid based path planning."""


class PathPlanner:
    """Right-angle movement planner: horizontal first, then vertical."""

    def next_position(self, x, y, tx, ty, speed):
        """Move up to `speed` units toward the target; return (x, y)."""
        remaining = speed
        dx = tx - x
        step = min(abs(dx), remaining)
        x += step if dx > 0 else -step
        remaining -= step
        dy = ty - y
        step = min(abs(dy), remaining)
        y += step if dy > 0 else -step
        return x, y

    def plan(self, start, end):
        """Return waypoints [start, corner, end] of the L-shaped route."""
        pts = [tuple(start)]
        if start[0] != end[0] and start[1] != end[1]:
            pts.append((end[0], start[1]))
        if tuple(end) != pts[-1]:
            pts.append(tuple(end))
        return pts

    def plan_multi(self, points):
        """Continuous route through several destinations."""
        route = []
        for a, b in zip(points, points[1:]):
            seg = self.plan(a, b)
            route.extend(seg if not route else seg[1:])
        return route or [tuple(points[0])] if points else []

    def path_length(self, points):
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                   for a, b in zip(points, points[1:]))
