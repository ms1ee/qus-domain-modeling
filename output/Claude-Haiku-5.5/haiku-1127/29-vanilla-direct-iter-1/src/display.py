"""Status reports and ASCII map rendering."""

import math
from typing import Any, List, Optional, Sequence, Tuple

from config import (
    CELL_SIZE,
    MAP_RESOLUTION,
    MAP_SIZE,
    STATE_NAMES,
)
from order_model import STATUS_COMPLETED, Order
from path_planner import PathPlanner
from rider import Rider

Point = Tuple[int, int]
Canvas = List[List[str]]


class DisplayManager:
    """Produces text reports and the command-line map visualisation.

    The map uses one character per ``MAP_RESOLUTION`` units, so the 800x800
    area becomes a 33x33 character canvas in which street lines fall every
    four characters (every 100 units).
    """

    LEGEND = "Legend: R=Rider  S=Restaurant  C=Customer  #=Street  *=Route  .=Empty"

    def __init__(self) -> None:
        """Create the display manager."""
        self._planner = PathPlanner()
        self._n = MAP_SIZE // MAP_RESOLUTION + 1

    # ------------------------------------------------------------------
    # Canvas helpers
    # ------------------------------------------------------------------
    def _to_rc(self, point: Point) -> Tuple[int, int]:
        """Convert a coordinate to ``(row, column)`` on the canvas.

        Row 0 is the top line, i.e. the largest y value.
        """
        x, y = point
        col = min(max(x, 0) // MAP_RESOLUTION, self._n - 1)
        row = self._n - 1 - min(max(y, 0) // MAP_RESOLUTION, self._n - 1)
        return row, col

    def _new_canvas(self) -> Canvas:
        """Create an empty canvas with street lines drawn as '#'."""
        n = self._n
        canvas = [["." for _ in range(n)] for _ in range(n)]
        for col in range(n):
            if (col * MAP_RESOLUTION) % CELL_SIZE == 0:
                for row in range(n):
                    canvas[row][col] = "#"
        for row in range(n):
            if ((n - 1 - row) * MAP_RESOLUTION) % CELL_SIZE == 0:
                for col in range(n):
                    canvas[row][col] = "#"
        return canvas

    def _place(self, canvas: Canvas, point: Point, symbol: str) -> None:
        """Draw a single symbol at a coordinate."""
        row, col = self._to_rc(point)
        canvas[row][col] = symbol

    def _draw_rect(self, canvas: Canvas, r1: int, c1: int, r2: int, c2: int) -> None:
        """Draw '*' over an axis-aligned span of canvas cells."""
        for row in range(min(r1, r2), max(r1, r2) + 1):
            for col in range(min(c1, c2), max(c1, c2) + 1):
                canvas[row][col] = "*"

    def _draw_polyline(self, canvas: Canvas, points: Sequence[Point]) -> None:
        """Draw a connected line segment graph through the given points."""
        for a, b in zip(points, points[1:]):
            r1, c1 = self._to_rc(a)
            r2, c2 = self._to_rc(b)
            if r1 != r2 and c1 != c2:
                # Not axis aligned: go through the corner.
                self._draw_rect(canvas, r1, c1, r1, c2)
                self._draw_rect(canvas, r1, c2, r2, c2)
            else:
                self._draw_rect(canvas, r1, c1, r2, c2)

    @staticmethod
    def cell_label(point: Point) -> str:
        """Return a coordinate with its grid cell index, e.g. ``(150,50) cell[1,0]``."""
        x, y = point
        return f"({x},{y}) cell[{x // CELL_SIZE},{y // CELL_SIZE}]"

    def render_map(
        self,
        riders: Sequence[Rider],
        orders: Sequence[Order],
        routes: Optional[Sequence[Sequence[Point]]] = None,
    ) -> str:
        """Render the ASCII map of riders, restaurants, customers and routes.

        Args:
            riders: Riders to draw as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are drawn.
                Completed orders are skipped.
            routes: Optional list of polylines drawn as '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = self._new_canvas()
        for route in routes or []:
            self._draw_polyline(canvas, route)
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            self._place(canvas, order.res_pos, "S")
            self._place(canvas, order.cus_pos, "C")
        for rider in riders:
            self._place(canvas, rider.position, "R")

        lines = []
        for row, cells in enumerate(canvas):
            y = (self._n - 1 - row) * MAP_RESOLUTION
            label = f"{y:>3} " if y % CELL_SIZE == 0 else "    "
            lines.append(label + "".join(cells))
        lines.append(f"    x: 0 to {MAP_SIZE} (1 char = {MAP_RESOLUTION} units, "
                     f"street every {CELL_SIZE} units)")
        lines.append("    " + self.LEGEND)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def status_report(self, system: Any) -> str:
        """Build the status snapshot of funds, riders and orders.

        Args:
            system: SystemManager instance.
        """
        riders = system.riders
        active = system.order_manager.active_orders()
        lines = [
            "=== System Status ===",
            f"Tick: {system.time}",
            f"System funds: {system.funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {len(system.order_manager.pending)}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} location=({rider.x},{rider.y}) "
                f"status={STATE_NAMES[rider.state]:<11} "
                f"orders={len(rider.orders)} {order_ids}"
            )
        lines.append(self.render_map(riders, active))
        return "\n".join(lines)

    def orders_report(self, orders: Sequence[Order]) -> str:
        """Build a table with the details of every order.

        Args:
            orders: Orders to display.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>14} {'Customer':>14} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':<10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.raw_res_pos[0]},{order.raw_res_pos[1]})"
            customer = f"({order.raw_cus_pos[0]},{order.raw_cus_pos[1]})"
            taken = str(order.duration) if order.duration is not None else "-"
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>14} "
                f"{customer:>14} {order.distance:>9} {taken:>6} "
                f"{rider:>6} {order.status:<10}"
            )
        return "\n".join(lines)

    def rider_log_report(self, riders: Sequence[Rider]) -> str:
        """Build the chronological status-change log of every rider.

        Args:
            riders: Riders whose logs should be shown.
        """
        if not riders:
            return "No riders have been recruited."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"--- Rider #{rider.rider_id} ---")
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:>4} {entry['event']:<20} "
                    f"order={order_text:<5} pos=({entry['x']},{entry['y']}) "
                    f"status={STATE_NAMES[entry['state']]}"
                )
        return "\n".join(lines)

    def start_report(self, order: Order, rider: Rider, new_rider: bool) -> str:
        """Build the report shown after an order is accepted.

        Includes grid coordinates, whether a rider was recruited, and the route
        map of the assigned rider with speed and estimated travel time.

        Args:
            order: The newly assigned order.
            rider: The rider that accepted the order.
            new_rider: True if a rider was recruited for this order.
        """
        pickup = self._planner.plan(rider.position, order.res_pos)
        delivery = self._planner.plan(order.res_pos, order.cus_pos)
        total = self._planner.route_length(rider.position, order.res_pos) + \
            self._planner.route_length(order.res_pos, order.cus_pos)
        ticks = math.ceil(total / rider.speed) if rider.speed > 0 else 0
        lines = [
            f"Order #{order.id} accepted by rider #{rider.rider_id}.",
            f"New rider added: {'yes' if new_rider else 'no'}",
            f"Restaurant input ({order.raw_res_pos[0]},{order.raw_res_pos[1]}) "
            f"-> grid {self.cell_label(order.res_pos)}",
            f"Customer   input ({order.raw_cus_pos[0]},{order.raw_cus_pos[1]}) "
            f"-> grid {self.cell_label(order.cus_pos)}",
            f"Rider speed: {rider.speed} units/tick",
            f"Route length: {total} units, estimated time: {ticks} ticks",
            "Route map:",
            self.render_map([rider], [order], routes=[pickup, delivery]),
        ]
        return "\n".join(lines)

    def queued_report(self, order: Order, funds: int) -> str:
        """Build the message shown when an order cannot be assigned yet.

        Args:
            order: The queued order.
            funds: Current system funds.
        """
        return (f"Order #{order.id} is queued: no rider is available and "
                f"funds ({funds}) are insufficient to recruit one.")
