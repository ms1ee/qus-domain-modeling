"""Grid-based path planning for the 800x800 delivery map.

The map is divided into an 8x8 grid of 100x100 unit cells. Lines whose x or y
coordinate is a multiple of 100 are streets. Movement prefers streets: a rider
that is on a street moves along it, a rider that is off the streets first snaps
onto the nearest street, and a rider directly above or below its target moves
straight towards it.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100

Point = Tuple[int, int]


class PathPlanner:
    """Plans axis-aligned, street-first movement on the map.

    All methods are stateless; the planner only computes positions. Riders do
    not block each other, so path conflicts cannot create deadlocks: every
    step strictly reduces the remaining distance to the target or moves a
    rider onto a street, which guarantees progress every tick.
    """

    @staticmethod
    def clamp(value: int) -> int:
        """Clamp a coordinate into the valid map range ``[0, MAP_SIZE]``.

        Args:
            value: Coordinate to clamp.

        Returns:
            The clamped coordinate.
        """
        return max(0, min(MAP_SIZE, value))

    @staticmethod
    def _sign(delta: int) -> int:
        """Return -1, 0 or 1 according to the sign of ``delta``."""
        return (delta > 0) - (delta < 0)

    @classmethod
    def nearest_street(cls, value: int) -> int:
        """Return the closest street line (multiple of 100) to a coordinate.

        Args:
            value: A single x or y coordinate.

        Returns:
            The nearest grid line coordinate inside the map.
        """
        return cls.clamp((value + CELL_SIZE // 2) // CELL_SIZE * CELL_SIZE)

    @staticmethod
    def is_on_street(x: int, y: int) -> bool:
        """Check whether a point lies on a street.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if x or y is aligned with a grid line.
        """
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @classmethod
    def is_special_case(cls, x: int, y: int, tx: int, ty: int) -> bool:
        """Determine whether the current position needs special handling.

        A special case is a rider directly above or below its target, or a
        rider that is currently off the street network.

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            tx: Target X coordinate.
            ty: Target Y coordinate.

        Returns:
            True if the special-case movement rules apply.
        """
        return x == tx or not cls.is_on_street(x, y)

    @classmethod
    def next_step(cls, x: int, y: int, tx: int, ty: int) -> Point:
        """Compute the position after one unit of movement towards a target.

        Priority rules:
            1. Already at the target: stay.
            2. Directly above/below the target: move vertically.
            3. On a horizontal street: move horizontally.
            4. On a vertical street: move vertically to the nearest street.
            5. Off the streets: snap to the nearest street (cheapest snap).

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            tx: Target X coordinate.
            ty: Target Y coordinate.

        Returns:
            The new ``(x, y)`` position after a single unit step.
        """
        if (x, y) == (tx, ty):
            return x, y

        # Special case: directly above or below the target.
        if x == tx:
            return x, cls.clamp(y + cls._sign(ty - y))

        # Street-first: travel horizontally along a horizontal street.
        if y % CELL_SIZE == 0:
            return cls.clamp(x + cls._sign(tx - x)), y

        # On a vertical street but off horizontal streets: reach a horizontal street.
        if x % CELL_SIZE == 0:
            ys = cls.nearest_street(y)
            return x, y + cls._sign(ys - y)

        # Off the street network: snap to the closest street line.
        ys = cls.nearest_street(y)
        xs = cls.nearest_street(x)
        if abs(ys - y) <= abs(xs - x):
            return x, y + cls._sign(ys - y)
        return x + cls._sign(xs - x), y

    @classmethod
    def plan_route(cls, start: Point, goal: Point, max_steps: int = 10000) -> List[Point]:
        """Compute the full unit-step route from a start point to a goal.

        Args:
            start: Starting ``(x, y)`` position.
            goal: Destination ``(x, y)`` position.
            max_steps: Safety limit on the number of steps.

        Returns:
            List of positions starting with ``start`` and ending at ``goal``
            (or at the last reached position if the limit is hit).
        """
        x, y = start
        path: List[Point] = [(x, y)]
        for _ in range(max_steps):
            if (x, y) == tuple(goal):
                break
            x, y = cls.next_step(x, y, goal[0], goal[1])
            path.append((x, y))
        if path[-1] != tuple(goal) and len(path) > 1:
            logger.warning("Route planning stopped before reaching goal %s", goal)
        return path
