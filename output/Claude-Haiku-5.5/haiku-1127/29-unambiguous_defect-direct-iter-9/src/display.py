"""Text rendering: ASCII map, status, order and rider reports."""

from typing import Iterable, List, Optional, Sequence

from config import CELL_SIZE, MAP_SIZE, STATE_NAMES
from path_planner import PathPlanner

SYMBOL_ROAD_H = "-"
SYMBOL_ROAD_V = "|"
SYMBOL_NODE = "+"
SYMBOL_EMPTY = " "
SYMBOL_RESTAURANT = "M"
SYMBOL_CUSTOMER = "C"
SYMBOL_ROUTE = "*"


class DisplayManager:
    """Produce text output for the command-line interface.

    The ASCII map uses a character canvas with two characters per 100-unit
    cell, so every street intersection sits on an even row and column.
    Rows are printed top (y = 800) to bottom (y = 0); columns are left (x = 0)
    to right (x = 800).
    """

    CANVAS_SIZE = 2 * (MAP_SIZE // CELL_SIZE) + 1

    def __init__(self, planner: Optional[PathPlanner] = None) -> None:
        self.planner = planner or PathPlanner()

    # ------------------------------------------------------------------
    # Map
    # ------------------------------------------------------------------
    def _cell(self, point: Sequence[int]):
        """Convert a map point to canvas ``(row, col)``."""
        scale = 2
        col = round(point[0] * scale / CELL_SIZE)
        row = self.CANVAS_SIZE - 1 - round(point[1] * scale / CELL_SIZE)
        return row, col

    def _put(self, canvas: List[List[str]], point: Sequence[int], symbol: str) -> None:
        """Place ``symbol`` on the canvas at the position of ``point``."""
        row, col = self._cell(point)
        if 0 <= row < self.CANVAS_SIZE and 0 <= col < self.CANVAS_SIZE:
            canvas[row][col] = symbol

    def _base_symbol(self, row: int, col: int) -> str:
        """Return the background symbol (intersection, street or empty)."""
        if row % 2 == 0 and col % 2 == 0:
            return SYMBOL_NODE
        if row % 2 == 0:
            return SYMBOL_ROAD_H
        if col % 2 == 0:
            return SYMBOL_ROAD_V
        return SYMBOL_EMPTY

    def render_map(
        self,
        riders: Iterable = (),
        orders: Iterable = (),
        route: Optional[Sequence[Sequence[int]]] = None,
    ) -> str:
        """Render the 8x8 cell map with riders, orders and an optional route.

        Symbols:
            ``+`` intersection, ``-``/``|`` street, ``M`` restaurant,
            ``C`` customer, ``0``-``9`` rider (last digit of the rider ID),
            ``*`` planned route.

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant and customer should be drawn.
            route: Optional list of points beginning with the rider position.

        Returns:
            Multi-line string containing the map and legend.
        """
        size = self.CANVAS_SIZE
        canvas = [[self._base_symbol(r, c) for c in range(size)] for r in range(size)]

        if route:
            for point in self.planner.dense_path(route[0], route[1:]):
                self._put(canvas, point, SYMBOL_ROUTE)

        for order in orders:
            if order.status in ("completed", "rejected"):
                continue
            self._put(canvas, order.res_pos, SYMBOL_RESTAURANT)
            self._put(canvas, order.cus_pos, SYMBOL_CUSTOMER)

        for rider in riders:
            self._put(canvas, (rider.x, rider.y), str(rider.rider_id % 10))

        lines = []
        for r, row in enumerate(canvas):
            label = f"{(size - 1 - r) * CELL_SIZE // 2:>4} " if r % 2 == 0 else "     "
            lines.append(label + "".join(row))
        lines.append("     x: 0 (left) -> 800 (right); y: 0 (bottom) -> 800 (top)")
        lines.append("     Legend: + node  - | street  M restaurant  C customer  "
                     "0-9 rider id  * route")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def render_status(self, system) -> str:
        """Render the system snapshot: funds, tick and rider states."""
        riders = system.riders
        lines = [
            f"Simulated tick : {system.tick_count}",
            f"System funds   : {system.funds}",
            f"Riders         : {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id:>2}: pos=({rider.x},{rider.y}) "
                f"state={STATE_NAMES.get(rider.state, 'unknown'):<10} "
                f"speed={rider.speed:>2} orders={len(rider.orders)} {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable) -> str:
        """Render a table of all orders with timing and assignment data."""
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>11}")
        lines = [header, "-" * len(header)]
        count = 0
        for order in orders:
            count += 1
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else str(order.rider_id)
            lines.append(
                f"{order.id:>4} {order.created_tick:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>6} {taken:>6} {rider:>6} {order.status:>11}"
            )
        if count == 0:
            lines.append("  (no orders yet)")
        return "\n".join(lines)

    def render_rider_log(self, riders: Iterable) -> str:
        """Render every recorded status change of every rider."""
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} (now {STATE_NAMES.get(rider.state, '?')}, "
                         f"at ({rider.x},{rider.y}))")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                state = STATE_NAMES.get(entry["state"], "?")
                lines.append(
                    f"  t={entry['tick']:>4} {entry['event']:<20} order={order:>4} "
                    f"at ({entry['x']},{entry['y']}) state={state}"
                )
        if not lines:
            return "No riders have been recruited yet."
        return "\n".join(lines)

    def render_event(self, entry) -> str:
        """Render a single event entry as a one-line message."""
        order = "" if entry["order_id"] is None else f" (order {entry['order_id']})"
        return (f"  [t={entry['tick']}] Rider {entry['rider_id']} {entry['event']}"
                f"{order} at ({entry['x']},{entry['y']})")
