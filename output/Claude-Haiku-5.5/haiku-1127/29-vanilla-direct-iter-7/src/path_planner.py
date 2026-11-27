"""Grid-based path planning for riders on the 8x8 street grid.

Movement rules (evaluated in order each step):
    1. Directly above/below the target (x equal): move vertically only.
    2. On the target row (y equal): move horizontally only.
    3. On a horizontal street (y is a multiple of 100): move horizontally.
    4. On a vertical street (x is a multiple of 100): move vertically.
    5. Inside a block: first move vertically to the nearest horizontal street.

Streets are preferred; the only off-street movement is the final approach
to a cell-centre target, which is the special "directly above or below" case.
"""

from constants import CELL_SIZE, MAP_SIZE


class PathPlanner:
    """Stateless helper that computes rider movement along the street grid."""

    @staticmethod
    def is_on_street(x, y):
        """Return True when the point lies on a street (grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            bool: True if x or y is a multiple of the cell size.
        """
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def nearest_street(value):
        """Return the nearest street coordinate to ``value`` within the map.

        Args:
            value: A coordinate along one axis.

        Returns:
            int: Nearest multiple of CELL_SIZE in the range [0, MAP_SIZE].
        """
        street = int(round(value / CELL_SIZE)) * CELL_SIZE
        return min(max(street, 0), MAP_SIZE)

    @staticmethod
    def _step(value, target, speed):
        """Move ``value`` toward ``target`` by at most ``speed``, never overshooting."""
        delta = target - value
        if abs(delta) <= speed:
            return target
        return value + speed if delta > 0 else value - speed

    @classmethod
    def next_position(cls, x, y, tx, ty, speed):
        """Compute the position after one tick of movement toward a target.

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            tx: Target X coordinate.
            ty: Target Y coordinate.
            speed: Maximum units to move this tick (>= 1).

        Returns:
            tuple[int, int]: The new (x, y) position.

        Raises:
            ValueError: If speed is less than 1.
        """
        if speed < 1:
            raise ValueError("speed must be at least 1 unit per tick")
        if x == tx and y == ty:
            return x, y
        # 1. Directly above or below the target: vertical approach.
        if x == tx:
            return x, cls._step(y, ty, speed)
        # 2. On the target row: horizontal approach.
        if y == ty:
            return cls._step(x, tx, speed), y
        # 3. On a horizontal street: travel along it.
        if y % CELL_SIZE == 0:
            return cls._step(x, tx, speed), y
        # 4. On a vertical street: travel along it.
        if x % CELL_SIZE == 0:
            return x, cls._step(y, ty, speed)
        # 5. Inside a block: reach the nearest horizontal street first.
        return x, cls._step(y, cls.nearest_street(y), speed)

    @classmethod
    def project_route(cls, start, stops, speed, max_steps=5000):
        """Project the tick-by-tick route through a sequence of stops.

        Args:
            start: (x, y) starting position.
            stops: Iterable of (x, y) destinations visited in order.
            speed: Units per tick.
            max_steps: Safety limit on the number of simulated steps per leg.

        Returns:
            tuple[list[tuple[int, int]], int]: The visited points (including
            the start) and the number of ticks required.

        Raises:
            RuntimeError: If a leg cannot be completed within ``max_steps``.
        """
        x, y = start
        points = [(x, y)]
        ticks = 0
        for tx, ty in stops:
            steps = 0
            while (x, y) != (tx, ty):
                x, y = cls.next_position(x, y, tx, ty, speed)
                points.append((x, y))
                ticks += 1
                steps += 1
                if steps > max_steps:
                    raise RuntimeError("route projection did not converge")
        return points, ticks
