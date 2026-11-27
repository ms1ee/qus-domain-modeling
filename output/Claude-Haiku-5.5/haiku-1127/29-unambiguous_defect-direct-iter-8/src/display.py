"""Text rendering: ASCII map, status, order and rider reports.

Map legend
----------
* ``+``  street junction
* ``-``  horizontal street segment
* ``|``  vertical street segment
* ``.``  cell centre (location area)
* ``M``  restaurant (active order)
* ``C``  customer (active order)
* ``*``  planned route
* ``0-9``  rider (ID modulo 10)
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from globalvar import CELL_SIZE, MAP_SIZE
from path_planner import (
    LATTICE_STEP,
    Point,
    grid_cell_of,
    is_cell_center,
    is_street_point,
)
from rider import Rider

_EMPTY = " "
_JUNCTION = "+"
_H_STREET = "-"
_V_STREET = "|"
_CENTRE = "."
_RESTAURANT = "M"
_CUSTOMER = "C"
_ROUTE = "*"


class DisplayManager:
    """Builds textual reports and the ASCII map.

    The map is drawn on a canvas with two characters per 50-unit lattice step,
    so streets, junctions, locations and riders are each visible.
    """

    @staticmethod
    def _canvas_pos(point: Point) -> Tuple[int, int]:
        """Map a map coordinate to a ``(row, column)`` canvas position.

        The y axis points up, so y = 800 is the top row.
        """
        x, y = point
        row = (2 * (MAP_SIZE - y)) // LATTICE_STEP
        col = (2 * x) // LATTICE_STEP
        return max(0, min(2 * (MAP_SIZE // LATTICE_STEP), row)), max(
            0, min(2 * (MAP_SIZE // LATTICE_STEP), col)
        )

    def _draw_segment(self, canvas: List[List[str]], a: Point, b: Point, char: str) -> None:
        """Draw ``char`` at the midpoint between two adjacent lattice points."""
        r1, c1 = self._canvas_pos(a)
        r2, c2 = self._canvas_pos(b)
        canvas[(r1 + r2) // 2][(c1 + c2) // 2] = char

    def render_map(
        self,
        riders: Iterable[Rider],
        orders: Optional[Iterable] = None,
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the 8x8 grid map as ASCII text.

        Args:
            riders: Riders to draw at their current positions.
            orders: Orders whose restaurant (M) and customer (C) locations are
                drawn.  Completed orders are skipped.
            route: Optional ordered waypoints to highlight with ``*``.  The
                first element is the starting point.

        Returns:
            Multi-line string containing the map and a legend.
        """
        lattice_n = MAP_SIZE // LATTICE_STEP
        size = 2 * lattice_n + 1
        canvas = [[_EMPTY] * size for _ in range(size)]

        # Streets.
        for i in range(lattice_n):
            for j in range(lattice_n + 1):
                y = j * LATTICE_STEP
                if y % CELL_SIZE == 0:
                    self._draw_segment(canvas, (i * LATTICE_STEP, y),
                                       ((i + 1) * LATTICE_STEP, y), _H_STREET)
        for i in range(lattice_n + 1):
            for j in range(lattice_n):
                x = i * LATTICE_STEP
                if x % CELL_SIZE == 0:
                    self._draw_segment(canvas, (x, j * LATTICE_STEP),
                                       (x, (j + 1) * LATTICE_STEP), _V_STREET)

        # Junctions and cell centres.
        for i in range(lattice_n + 1):
            for j in range(lattice_n + 1):
                point = (i * LATTICE_STEP, j * LATTICE_STEP)
                row, col = self._canvas_pos(point)
                if is_street_point(*point):
                    canvas[row][col] = _JUNCTION
                elif is_cell_center(*point):
                    canvas[row][col] = _CENTRE

        # Route overlay.
        if route:
            previous = route[0]
            for point in route[1:]:
                self._draw_segment(canvas, previous, point, _ROUTE)
                row, col = self._canvas_pos(point)
                canvas[row][col] = _ROUTE
                previous = point
            row, col = self._canvas_pos(route[0])
            canvas[row][col] = _ROUTE

        # Active order locations.
        for order in orders or []:
            if order.status == "completed":
                continue
            row, col = self._canvas_pos(order.res_pos)
            canvas[row][col] = _RESTAURANT
            row, col = self._canvas_pos(order.cus_pos)
            canvas[row][col] = _CUSTOMER

        # Riders drawn last so they stay visible.
        for rider in riders:
            row, col = self._canvas_pos(rider.position())
            canvas[row][col] = str(rider.rider_id % 10)

        lines = ["".join(row).rstrip() for row in canvas]
        legend = (
            "Legend: + junction  - | street  . cell centre  "
            "M restaurant  C customer  * route  0-9 rider id"
        )
        return "\n".join(lines) + "\n" + legend

    @staticmethod
    def format_status(funds: int, tick: int, riders: Sequence[Rider]) -> str:
        """Return the system status snapshot.

        Args:
            funds: Current fund balance.
            tick: Current simulated tick.
            riders: All riders.
        """
        lines = [
            f"=== System status @ tick {tick} ===",
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            cell = grid_cell_of(rider.position())
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x},{rider.y}) "
                f"cell={cell} state={rider.state_name()} "
                f"orders={len(order_ids)} {order_ids} speed={rider.speed}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders: Sequence) -> str:
        """Return a report of every order.

        Args:
            orders: All orders in creation order.
        """
        if not orders:
            return "No orders yet."
        lines = [f"=== Orders ({len(orders)}) ==="]
        for order in orders:
            taken = order.time_taken if order.time_taken is not None else "-"
            rider = order.rider_id if order.rider_id is not None else "-"
            lines.append(
                f"  #{order.id} start_tick={order.start_time} "
                f"restaurant={order.res_pos} cell={grid_cell_of(order.res_pos)} "
                f"customer={order.cus_pos} cell={grid_cell_of(order.cus_pos)} "
                f"distance={order.distance} time_taken={taken} "
                f"rider={rider} status={order.status}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders: Sequence[Rider]) -> str:
        """Return every recorded status change for all riders.

        Args:
            riders: All riders.
        """
        if not riders:
            return "No riders recruited yet."
        lines = ["=== Rider event log ==="]
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  tick={entry['tick']} event={entry['event']} "
                    f"order={order} position=({entry['x']},{entry['y']}) "
                    f"state={entry['state']}"
                )
        return "\n".join(lines)
