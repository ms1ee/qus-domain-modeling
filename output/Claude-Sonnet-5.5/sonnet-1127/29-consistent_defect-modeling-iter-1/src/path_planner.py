"""Grid-based path planning."""


class PathPlanner:
    """Plans movement along streets (axis aligned)."""

    def next_position(self, x, y, tx, ty, speed):
        """Return position after moving up to `speed` units toward target.

        Moves horizontally first, then vertically (right-angle turn).
        If already aligned on x, moves vertically directly.
        """
        budget = speed
        if x != tx:
            step = min(budget, abs(tx - x))
            x += step if tx > x else -step
            budget -= step
        if budget > 0 and y != ty:
            step = min(budget, abs(ty - y))
            y += step if ty > y else -step
        return x, y

    def plan(self, start, goals, speed=20):
        """Return list of waypoints (per tick) through the goals in order."""
        x, y = start
        pts = [(x, y)]
        for gx, gy in goals:
            guard = 0
            while (x, y) != (gx, gy) and guard < 10000:
                x, y = self.next_position(x, y, gx, gy, speed)
                pts.append((x, y))
                guard += 1
        return pts
