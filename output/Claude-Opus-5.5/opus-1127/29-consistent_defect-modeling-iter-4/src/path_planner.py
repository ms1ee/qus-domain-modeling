"""Grid based path planning for riders.

The map is an 800x800 coordinate plane divided into 100x100 cells.  Lines
at multiples of 100 are treated as streets; riders prefer to travel along
them, making right-angle turns where necessary.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE


class GridMap:
    """Description of the map geometry."""

    def __init__(self, width=MAP_SIZE, height=MAP_SIZE, cell_size=CELL_SIZE):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid_dimension = width // cell_size

    def clamp(self, value):
        """Clamp a coordinate to the map range."""
        return max(0, min(self.width, int(value)))

    def to_grid_corner(self, x, y):
        """Convert raw coordinates to the top-left corner of their cell."""
        x = self.clamp(x)
        y = self.clamp(y)
        return (x // self.cell_size) * self.cell_size, \
            (y // self.cell_size) * self.cell_size

    def to_grid_center(self, x, y):
        """Convert raw coordinates to the center of their cell."""
        x = min(self.clamp(x), self.width - 1)
        y = min(self.clamp(y), self.height - 1)
        return (x // self.cell_size) * self.cell_size + self.cell_size // 2, \
            (y // self.cell_size) * self.cell_size + self.cell_size // 2

    def is_street(self, x, y):
        """Return True if the point lies on a street line."""
        return x % self.cell_size == 0 or y % self.cell_size == 0


def manhattan(a, b):
    """Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a, b):
    """Euclidean distance between two points."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


class Route:
    """A sequence of waypoints with an estimated travel time."""

    def __init__(self, points, speed=20):
        self.points = list(points)
        self.speed = speed
        self.length = sum(manhattan(self.points[i], self.points[i + 1])
                          for i in range(len(self.points) - 1))
        if speed > 0:
            self.estimated_time = -(-self.length // speed)
        else:
            self.estimated_time = 0

    def extend(self, other):
        """Append another route (skipping the duplicated joint point)."""
        pts = list(other.points)
        if self.points and pts and tuple(self.points[-1]) == tuple(pts[0]):
            pts = pts[1:]
        return Route(self.points + pts, self.speed)


class PathPlanner:
    """Plans right-angle paths preferring streets."""

    def __init__(self, grid_map=None):
        self.grid_map = grid_map or GridMap()

    def plan_points(self, start, end):
        """Return a list of waypoints (including start and end).

        Returns a tuple ``(points, special_case)`` where ``special_case`` is
        True when the rider is directly above/below or beside the target.
        """
        sx, sy = int(start[0]), int(start[1])
        ex, ey = int(end[0]), int(end[1])
        if (sx, sy) == (ex, ey):
            return [(sx, sy)], False
        if sx == ex or sy == ey:
            # Directly above/below (or on the same row): straight line.
            return [(sx, sy), (ex, ey)], True
        cs = self.grid_map.cell_size
        # Prefer the first leg that lies on a street.
        if sy % cs == 0:
            corner = (ex, sy)          # horizontal first along street
        elif sx % cs == 0:
            corner = (sx, ey)          # vertical first along street
        elif ey % cs == 0:
            corner = (sx, ey)          # second leg horizontal on street
        else:
            corner = (ex, sy)
        return [(sx, sy), corner, (ex, ey)], False

    def plan_route(self, start, end, speed=20):
        """Plan a Route from start to end."""
        points, _ = self.plan_points(start, end)
        return Route(points, speed)

    def plan_multi(self, start, destinations, speed=20):
        """Plan a continuous route through several destinations."""
        route = Route([tuple(start)], speed)
        current = tuple(start)
        for dest in destinations:
            route = route.extend(self.plan_route(current, dest, speed))
            current = tuple(dest)
        return route

    @staticmethod
    def advance_along(x, y, waypoints, budget):
        """Move from (x, y) along ``waypoints`` using at most ``budget`` units.

        ``waypoints`` is consumed in place as points are reached.
        Returns the new position and the distance travelled.
        """
        travelled = 0
        while waypoints and budget > 0:
            tx, ty = waypoints[0]
            dist = abs(tx - x) + abs(ty - y)
            if dist == 0:
                waypoints.pop(0)
                continue
            step = min(budget, dist)
            if tx != x:
                dx = min(step, abs(tx - x))
                x += dx if tx > x else -dx
                step_used = dx
            else:
                dy = min(step, abs(ty - y))
                y += dy if ty > y else -dy
                step_used = dy
            budget -= step_used
            travelled += step_used
            if (x, y) == (tx, ty):
                waypoints.pop(0)
        return x, y, travelled
