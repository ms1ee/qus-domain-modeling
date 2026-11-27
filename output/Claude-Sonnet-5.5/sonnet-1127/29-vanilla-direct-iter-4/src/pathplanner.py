"""Grid path planning."""


class PathPlanner:
    """Street-based pathfinding."""

    @staticmethod
    def _step(a, b, d):
        if abs(b - a) <= d:
            return b
        return a + d if b > a else a - d

    @staticmethod
    def next_point(x, y, tx, ty, speed):
        """Return the next position after moving up to speed units."""
        left = speed
        while left > 0 and (x, y) != (tx, ty):
            on_v = x % 100 == 0
            on_h = y % 100 == 0
            if on_v and on_h:
                pass
            if not on_v and not on_h:
                # go to nearest vertical street horizontally
                gx = round(x / 100) * 100
                if abs(gx - x) == 50:
                    gx = x - 50
                nx = PathPlanner._step(x, gx, left)
                left -= abs(nx - x)
                x = nx
                continue
            if y == ty or x == tx:
                if y == ty and x != tx:
                    nx = PathPlanner._step(x, tx, left)
                    left -= abs(nx - x)
                    x = nx
                else:
                    ny = PathPlanner._step(y, ty, left)
                    left -= abs(ny - y)
                    y = ny
                continue
            if on_v:
                # travel vertically along street toward target row street
                gy = ty if ty % 100 == 0 else (ty // 100) * 100
                if y == gy:
                    nx = PathPlanner._step(x, tx, left)
                    left -= abs(nx - x)
                    x = nx
                else:
                    ny = PathPlanner._step(y, gy, left)
                    left -= abs(ny - y)
                    y = ny
            else:
                gx = tx if tx % 100 == 0 else (tx // 100) * 100
                if x == gx:
                    ny = PathPlanner._step(y, ty, left)
                    left -= abs(ny - y)
                    y = ny
                else:
                    nx = PathPlanner._step(x, gx, left)
                    left -= abs(nx - x)
                    x = nx
        return x, y

    @staticmethod
    def route(x, y, tx, ty, speed=10):
        """Return list of points visited, tick by tick."""
        pts = [(x, y)]
        for _ in range(10000):
            if (x, y) == (tx, ty):
                break
            x, y = PathPlanner.next_point(x, y, tx, ty, speed)
            pts.append((x, y))
        return pts
