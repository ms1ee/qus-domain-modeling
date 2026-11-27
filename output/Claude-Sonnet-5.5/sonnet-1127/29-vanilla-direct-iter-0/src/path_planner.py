"""Grid based path planning."""

CELL = 100


class PathPlanner:
    """Moves along axes: horizontal first, then vertical."""

    @staticmethod
    def next_position(x, y, tx, ty, speed):
        """Advance up to `speed` units toward the target."""
        budget = speed
        if x != tx:
            step = min(budget, abs(tx - x))
            x += step if tx > x else -step
            budget -= step
        if budget > 0 and y != ty:
            step = min(budget, abs(ty - y))
            y += step if ty > y else -step
        return x, y

    @staticmethod
    def corner_points(points):
        """Return the polyline (with right-angle corners) through points."""
        if not points:
            return []
        result = [points[0]]
        for px, py in points[1:]:
            cx, cy = result[-1]
            if cx != px and cy != py:
                result.append((px, cy))
            if result[-1] != (px, py):
                result.append((px, py))
        return result

    @staticmethod
    def cells_on_path(points):
        """Return the set of grid cells (col,row) touched by the path."""
        cells = []
        poly = PathPlanner.corner_points(points)
        for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
            n = max(abs(x2 - x1), abs(y2 - y1))
            for i in range(0, n + 1, 10 if n >= 10 else 1):
                px = x1 + (x2 - x1) * i // n if n else x1
                py = y1 + (y2 - y1) * i // n if n else y1
                c = (min(px // CELL, 7), min(py // CELL, 7))
                if c not in cells:
                    cells.append(c)
        return cells

    @staticmethod
    def path_length(points):
        """Manhattan length of the polyline."""
        poly = PathPlanner.corner_points(points)
        return sum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                   for a, b in zip(poly, poly[1:]))
