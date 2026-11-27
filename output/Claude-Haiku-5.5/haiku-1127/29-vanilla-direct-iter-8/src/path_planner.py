"""Grid-based path planning for riders.

The map is a grid of streets located on multiples of the cell size (100).
A point is on a street when its x or y coordinate is a multiple of 100.
Routes are sequences of axis-aligned waypoints: the rider first reaches a
street if it is off-grid, then travels along streets with right-angle turns,
and finally makes the short approach to the destination.

Because riders never block each other in this model, route planning cannot
produce waiting cycles, so deadlocks cannot occur.
"""

from config import SETTINGS


class PathPlanner:
    """Stateless helper providing route computation on the street grid."""

    @staticmethod
    def is_street(x, y):
        """Check whether a point lies on a street.

        Args:
            x: x coordinate.
            y: y coordinate.

        Returns:
            bool: True if x or y is a multiple of the cell size.
        """
        cell = SETTINGS["cell_size"]
        return x % cell == 0 or y % cell == 0

    @staticmethod
    def nearest_grid_line(value):
        """Return the nearest grid line coordinate within the map.

        Args:
            value: Coordinate to round.

        Returns:
            int: A multiple of the cell size between 0 and the map size.
        """
        cell = SETTINGS["cell_size"]
        size = SETTINGS["map_size"]
        line = int(round(value / cell)) * cell
        return min(max(line, 0), size)

    @classmethod
    def snap_to_street(cls, x, y):
        """Move an off-street point to the nearest street with one axis change.

        Args:
            x: x coordinate.
            y: y coordinate.

        Returns:
            tuple: ``(x, y)`` on a street, changing only one coordinate.
        """
        if cls.is_street(x, y):
            return (x, y)
        grid_x = cls.nearest_grid_line(x)
        grid_y = cls.nearest_grid_line(y)
        cost_x = abs(x - grid_x)
        cost_y = abs(y - grid_y)
        if cost_x <= cost_y:
            return (grid_x, y)
        return (x, grid_y)

    @classmethod
    def plan_route(cls, start, goal):
        """Compute waypoints from ``start`` to ``goal`` (start excluded).

        Strategy:
            * Off-street start: first snap onto the nearest street.
            * Directly above/below or beside the goal: a straight segment.
            * Otherwise: travel along the street the rider is on, then turn
              once toward the goal (right-angle turn).

        Args:
            start: Current ``(x, y)`` position.
            goal: Destination ``(x, y)``.

        Returns:
            list[tuple]: Axis-aligned waypoints ending at the goal.
        """
        cell = SETTINGS["cell_size"]
        waypoints = []
        current = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))

        if not cls.is_street(*current):
            current = cls.snap_to_street(*current)
            waypoints.append(current)
        if current == goal:
            return waypoints

        goal_x, goal_y = goal
        if current[0] == goal_x or current[1] == goal_y:
            waypoints.append(goal)
        elif current[1] % cell == 0:
            # On a horizontal street: drive along it, then turn toward goal.
            waypoints.append((goal_x, current[1]))
            waypoints.append(goal)
        else:
            # On a vertical street: drive along it, then turn toward goal.
            waypoints.append((current[0], goal_y))
            waypoints.append(goal)
        return waypoints

    @classmethod
    def plan_multi_stop(cls, start, stops):
        """Plan one continuous route through several stops in order.

        Args:
            start: Starting ``(x, y)`` position.
            stops: Ordered list of ``(x, y)`` destinations.

        Returns:
            list[tuple]: Concatenated waypoints for the whole trip.
        """
        route = []
        current = start
        for stop in stops:
            route.extend(cls.plan_route(current, stop))
            current = stop
        return route

    @staticmethod
    def route_length(start, waypoints):
        """Return the total street distance of a route.

        Args:
            start: Starting ``(x, y)`` position.
            waypoints: Waypoints as returned by ``plan_route``.

        Returns:
            int: Total Manhattan length of the route.
        """
        total = 0
        current = start
        for point in waypoints:
            total += abs(point[0] - current[0]) + abs(point[1] - current[1])
            current = point
        return total
