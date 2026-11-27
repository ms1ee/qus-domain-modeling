"""Grid-based path planning for rider movement.

Riders travel only along streets. The planner returns one movement step per
tick; each step never leaves the street network and always makes progress
toward the target, so riders cannot livelock. Riders do not block each other,
which means path conflicts never stall a rider.
"""

import config
import grid


def _toward(value, target, step):
    """Move ``value`` toward ``target`` by at most ``step`` units.

    Args:
        value: Current coordinate.
        target: Desired coordinate.
        step: Maximum movement in this call (positive int).

    Returns:
        int: New coordinate, never overshooting ``target``.
    """
    if value == target:
        return value
    delta = target - value
    move = min(step, abs(delta))
    return value + move if delta > 0 else value - move


class PathPlanner:
    """Stateless planner that computes street-constrained movement steps."""

    @staticmethod
    def next_step(x, y, tx, ty, speed):
        """Compute the next position of a rider heading to ``(tx, ty)``.

        Movement rules:
            * At an intersection, travel horizontally until aligned with the
              target column, then vertically (right-angle turns).
            * On a horizontal street (mid-block), move horizontally toward the
              target column.
            * On a vertical street (mid-block), move vertically toward the
              target row.
            * Directly above/below the target (same column) is a special
              case: the rider moves vertically only and ``special_case`` is
              reported as True.

        Args:
            x: Current x coordinate (must be on a street).
            y: Current y coordinate (must be on a street).
            tx: Target x coordinate (normally a street intersection).
            ty: Target y coordinate (normally a street intersection).
            speed: Maximum units to travel this tick.

        Returns:
            tuple[int, int, bool]: ``(new_x, new_y, special_case)``.
        """
        if (x, y) == (tx, ty):
            return x, y, False

        step = max(1, int(speed))
        on_horizontal = y % config.CELL_SIZE == 0
        on_vertical = x % config.CELL_SIZE == 0

        if on_horizontal and on_vertical:
            if x != tx:
                new_x, new_y = _toward(x, tx, step), y
            else:
                new_x, new_y = x, _toward(y, ty, step)
        elif on_horizontal:
            new_x, new_y = _toward(x, tx, step), y
        elif on_vertical:
            new_x, new_y = x, _toward(y, ty, step)
        else:
            # Off-road point (should not happen): join the nearest vertical street.
            half = config.CELL_SIZE // 2
            street_x = min(
                config.MAP_SIZE,
                ((x + half) // config.CELL_SIZE) * config.CELL_SIZE,
            )
            new_x, new_y = _toward(x, street_x, step), y

        special = new_x == tx and new_y != ty
        return new_x, new_y, special

    @staticmethod
    def route_length(a, b):
        """Return the street-network length estimate between two points.

        Args:
            a: ``(x, y)`` start point.
            b: ``(x, y)`` end point.

        Returns:
            int: Manhattan distance, which equals the L-shaped route length.
        """
        return grid.manhattan(a, b)
