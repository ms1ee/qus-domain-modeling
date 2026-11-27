"""Grid path planning."""


def center(v):
    """Convert coordinate to grid cell center."""
    v = max(0, min(799, int(v)))
    return (v // 100) * 100 + 50


class PathPlanner:
    """Simple L-shaped path planner."""

    @staticmethod
    def step(x, y, tx, ty, speed):
        """Move up to speed units toward target, horizontal first."""
        left = speed
        dx = tx - x
        if dx and left:
            m = min(abs(dx), left)
            x += m if dx > 0 else -m
            left -= m
        dy = ty - y
        if dy and left:
            m = min(abs(dy), left)
            y += m if dy > 0 else -m
        return x, y
