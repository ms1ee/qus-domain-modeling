"""Grid-based path planning along streets."""

import math

from gridmap import CELL_SIZE, MAP_SIZE

HALF = CELL_SIZE // 2


class Route:
    """A planned route made of axis-aligned segments."""

    def __init__(self, points, speed=10):
        self.points = list(points)
        self.speed = speed
        self.length = PathPlanner.path_length(self.points)
        if speed and speed > 0:
            self.estimated_time = int(math.ceil(self.length / float(speed)))
        else:
            self.estimated_time = 0

    def __repr__(self):
        return "Route(points={}, length={}, estimated_time={})".format(
            self.points, self.length, self.estimated_time)


class PathPlanner:
    """Plans rider paths on the 8x8 grid, preferring streets."""

    @staticmethod
    def _dedupe(points):
        result = []
        for p in points:
            if not result or result[-1] != p:
                result.append(p)
        return result

    @staticmethod
    def _nearest_line(value, toward):
        """Return the street line (multiple of 100) nearest to ``value``.

        Ties are broken toward ``toward``.
        """
        lower = (value // CELL_SIZE) * CELL_SIZE
        upper = min(MAP_SIZE, lower + CELL_SIZE)
        d_low = value - lower
        d_up = upper - value
        if d_low < d_up:
            return lower
        if d_up < d_low:
            return upper
        return upper if toward > value else lower

    @staticmethod
    def plan_points(start, target):
        """Plan a path from ``start`` to ``target``.

        Returns:
            tuple(list[tuple[int, int]], bool): the waypoints (including start
            and target) and whether a special case (rider directly above or
            below the target) was handled.
        """
        sx, sy = int(start[0]), int(start[1])
        tx, ty = int(target[0]), int(target[1])
        pts = [(sx, sy)]
        if (sx, sy) == (tx, ty):
            return pts, False
        special = (sx == tx and sy != ty)

        on_v = sx % CELL_SIZE == 0
        on_h = sy % CELL_SIZE == 0

        if not on_v and not on_h:
            # Same cell: move straight inside the block.
            if sx // CELL_SIZE == tx // CELL_SIZE and sy // CELL_SIZE == ty // CELL_SIZE:
                pts.append((tx, sy))
                pts.append((tx, ty))
                return PathPlanner._dedupe(pts), special
            vx = PathPlanner._nearest_line(sx, tx)
            hy = PathPlanner._nearest_line(sy, ty)
            dx = abs(vx - sx)
            dy = abs(hy - sy)
            if dy < dx or (dy == dx and ty != sy):
                sy = hy
                on_h = True
            else:
                sx = vx
                on_v = True
            pts.append((sx, sy))

        if on_h:
            if abs(ty - sy) == HALF:
                pts.append((tx, sy))
                pts.append((tx, ty))
            else:
                left, right = tx - HALF, tx + HALF
                if abs(sx - left) <= abs(sx - right):
                    vx = left
                else:
                    vx = right
                pts.append((vx, sy))
                pts.append((vx, ty))
                pts.append((tx, ty))
        else:
            if abs(tx - sx) == HALF:
                pts.append((sx, ty))
                pts.append((tx, ty))
            else:
                up, down = ty - HALF, ty + HALF
                if abs(sy - up) <= abs(sy - down):
                    hy = up
                else:
                    hy = down
                pts.append((sx, hy))
                pts.append((tx, hy))
                pts.append((tx, ty))
        return PathPlanner._dedupe(pts), special

    @staticmethod
    def path_length(points):
        """Return the length of a polyline (Manhattan per segment)."""
        total = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    @staticmethod
    def plan_multi(start, stops):
        """Plan a continuous path through several stops."""
        points = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            seg, _ = PathPlanner.plan_points(current, stop)
            points.extend(seg[1:])
            current = tuple(stop)
        return PathPlanner._dedupe(points)

    @staticmethod
    def plan_route(start, stops, speed=10):
        """Plan a :class:`Route` through ``stops`` starting at ``start``."""
        return Route(PathPlanner.plan_multi(start, stops), speed)
