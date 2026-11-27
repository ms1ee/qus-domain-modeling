"""Grid-based path planning for riders.

The map is an 8x8 grid of 100x100 cells. Roads run along the grid lines, i.e.
points where ``x`` or ``y`` is a multiple of the cell size. Riders always move
along these streets, making right-angle turns at intersections.
"""

from typing import List, Sequence, Tuple

from config import CELL_SIZE, GRID_DIMENSION

Point = Tuple[int, int]


class PathPlanner:
    """Compute street-following movement and routes on the grid.

    Movement rules:
        * If the rider is on a horizontal street (``y`` on a grid line) and
          has not reached the target ``x``, it moves horizontally.
        * Otherwise, if the rider is on a vertical street (``x`` on a grid
          line) and has not reached the target ``y``, it moves vertically.
        * Targets are always grid intersections, so the rider reaches them
          by travelling along streets only.

    Special cases:
        * A rider directly above or below its target (same ``x``, different
          ``y``) is flagged through :meth:`is_directly_above_or_below`.
    """

    def __init__(self, grid_dimension: int = GRID_DIMENSION,
                 cell_size: int = CELL_SIZE) -> None:
        """Create a planner for a grid of the given dimension and cell size.

        Args:
            grid_dimension: Number of cells per side of the grid.
            cell_size: Size of one grid cell in map units.
        """
        self.grid_dimension = grid_dimension
        self.cell_size = cell_size

    def is_on_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line).

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_directly_above_or_below(self, x: int, y: int,
                                   tx: int, ty: int) -> bool:
        """Return True if the point shares the target's x but not its y.

        Such positions need a purely vertical approach and are flagged as
        special cases on the rider.
        """
        return x == tx and y != ty

    def next_position(self, x: int, y: int, tx: int, ty: int,
                      distance: int) -> Tuple[int, int, int]:
        """Advance up to ``distance`` units along streets toward a target.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            distance: Maximum distance to travel this tick.

        Returns:
            A tuple ``(new_x, new_y, travelled)`` where ``travelled`` is the
            Manhattan distance actually covered.
        """
        cs = self.cell_size
        travelled = 0
        remaining = distance
        while remaining > 0 and (x, y) != (tx, ty):
            if y % cs == 0 and x != tx:
                delta = tx - x
                step = min(abs(delta), remaining)
                x += step if delta > 0 else -step
            elif x % cs == 0 and y != ty:
                delta = ty - y
                step = min(abs(delta), remaining)
                y += step if delta > 0 else -step
            else:
                # Off-street position: cannot happen with snapped targets,
                # but stop rather than loop forever.
                break
            travelled += step
            remaining -= step
        return x, y, travelled

    def route_corners(self, start: Sequence[int],
                      waypoints: Sequence[Sequence[int]]) -> List[Point]:
        """Build the street route from ``start`` through each waypoint.

        Args:
            start: Starting ``(x, y)`` position.
            waypoints: Ordered destinations, e.g. ``[restaurant, customer]``.

        Returns:
            Ordered list of corner points, beginning with ``start``.
        """
        current = (int(start[0]), int(start[1]))
        points: List[Point] = [current]
        for target in waypoints:
            target_pt = (int(target[0]), int(target[1]))
            points.extend(self._segment_corners(current, target_pt))
            current = target_pt
        return points

    def route_length(self, points: Sequence[Point]) -> int:
        """Return the total street distance along a list of route points."""
        total = 0
        for a, b in zip(points, points[1:]):
            total += abs(b[0] - a[0]) + abs(b[1] - a[1])
        return total

    def _segment_corners(self, a: Point, b: Point) -> List[Point]:
        """Return the points needed to travel from ``a`` to ``b`` on streets.

        The returned list excludes ``a`` and includes ``b`` as its last item.
        """
        ax, ay = a
        bx, by = b
        if (ax, ay) == (bx, by):
            return []
        if ax == bx or ay == by:
            return [b]
        if ay % self.cell_size == 0:
            corner = (bx, ay)   # Horizontal first along a horizontal street.
        else:
            corner = (ax, by)   # Vertical first along a vertical street.
        return [corner, b]
