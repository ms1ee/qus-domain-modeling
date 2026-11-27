"""Grid path planning."""


class PathPlanner:
    """Right-angle grid pathfinding (horizontal first, then vertical)."""

    @staticmethod
    def next_position(x, y, tx, ty, speed):
        """Move up to `speed` units from (x,y) toward (tx,ty)."""
        budget = speed
        dx = tx - x
        step = min(abs(dx), budget)
        x += step if dx > 0 else -step
        budget -= step
        dy = ty - y
        step = min(abs(dy), budget)
        y += step if dy > 0 else -step
        return x, y

    @staticmethod
    def waypoints(points):
        """Return corner list for a multi-destination path."""
        pts = [points[0]]
        for (x, y) in points[1:]:
            px, py = pts[-1]
            if px != x and py != y:
                pts.append((x, py))
            pts.append((x, y))
        return pts

    @staticmethod
    def cells(points):
        """Grid cells (col,row) traversed by the path."""
        wps = PathPlanner.waypoints(points)
        out = []
        for (ax, ay), (bx, by) in zip(wps, wps[1:]):
            n = max(abs(bx - ax), abs(by - ay)) // 10 + 1
            for i in range(n + 1):
                px = ax + (bx - ax) * i // n
                py = ay + (by - ay) * i // n
                c = (min(px // 100, 7), min(py // 100, 7))
                if c not in out:
                    out.append(c)
        return out
