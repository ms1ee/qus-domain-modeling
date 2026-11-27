"""Status tables, event logs and ASCII map rendering."""

import math
from typing import Iterable, List, Optional, Sequence, Tuple

from config import CELL_SIZE, LATTICE_STEP, MAP_SIZE
from pathplanner import PathPlanner
from rider import STATE_NAMES

Point = Tuple[int, int]


class DisplayManager:
    """Builds text output for the command-line interface.

    Symbols:
        R rider, M restaurant, C customer, + intersection,
        - and | street segments, * route, space for empty map cells.
    """

    rider_symbol = "R"
    restaurant_symbol = "M"
    customer_symbol = "C"
    intersection_symbol = "+"
    street_h = "-"
    street_v = "|"
    route_symbol = "*"
    empty_symbol = " "

    # ------------------------------------------------------------------ #
    # Coordinate helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _row(y: int) -> int:
        """Map a y coordinate to a canvas row (y=800 is the top row)."""
        return 2 * (MAP_SIZE // LATTICE_STEP - y // LATTICE_STEP)

    @staticmethod
    def _col(x: int) -> int:
        """Map an x coordinate to a canvas column."""
        return 2 * (x // LATTICE_STEP)

    # ------------------------------------------------------------------ #
    # Map
    # ------------------------------------------------------------------ #
    def render_map(self, riders: Iterable = (), orders: Iterable = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the 8x8 grid as an ASCII map.

        Args:
            riders: Riders to mark on the map.
            orders: Orders whose restaurants and customers are marked.
            route: Optional polyline (starting at the rider) to highlight.

        Returns:
            Multi-line string containing the map, axis labels and legend.
        """
        n = MAP_SIZE // LATTICE_STEP
        size = 2 * n + 1
        canvas: List[List[str]] = [[self.empty_symbol] * size for _ in range(size)]

        for xi in range(n + 1):
            for yi in range(n + 1):
                x, y = xi * LATTICE_STEP, yi * LATTICE_STEP
                if PathPlanner.is_location((x, y)):
                    continue
                r, c = self._row(y), self._col(x)
                if x % CELL_SIZE == 0 and y % CELL_SIZE == 0:
                    canvas[r][c] = self.intersection_symbol
                if xi < n and y % CELL_SIZE == 0:
                    canvas[r][c + 1] = self.street_h
                if yi < n and x % CELL_SIZE == 0:
                    canvas[r - 1][c] = self.street_v

        if route:
            for a, b in zip(route, route[1:]):
                ra, ca = self._row(a[1]), self._col(a[0])
                rb, cb = self._row(b[1]), self._col(b[0])
                canvas[(ra + rb) // 2][(ca + cb) // 2] = self.route_symbol
                for point, rr, cc in ((a, ra, ca), (b, rb, cb)):
                    if not PathPlanner.is_location(point):
                        canvas[rr][cc] = self.route_symbol

        for order in orders:
            if order.status in ("completed", "cancelled"):
                continue
            rr, cc = self._row(order.restaurant_y), self._col(order.restaurant_x)
            canvas[rr][cc] = self.restaurant_symbol
            rr, cc = self._row(order.customer_y), self._col(order.customer_x)
            canvas[rr][cc] = self.customer_symbol

        for rider in riders:
            px, py = rider.snapped_position()
            canvas[self._row(py)][self._col(px)] = self.rider_symbol

        lines: List[str] = []
        for row_index, row in enumerate(canvas):
            label = " " * 5
            if row_index % 2 == 0:
                y = MAP_SIZE - (row_index // 2) * LATTICE_STEP
                if y % CELL_SIZE == 0:
                    label = f"{y:>4} "
            lines.append(label + "".join(row))

        header = [" "] * (5 + size + 4)
        for xi in range(n + 1):
            x = xi * LATTICE_STEP
            if x % CELL_SIZE:
                continue
            text = str(x)
            start = 5 + self._col(x) - len(text) // 2
            for offset, ch in enumerate(text):
                if 0 <= start + offset < len(header):
                    header[start + offset] = ch
        lines.insert(0, "".join(header).rstrip())
        lines.append("")
        lines.append("Legend: R rider  M restaurant  C customer  + intersection  "
                     "-/| street  * route")
        lines.append("Coordinates in units: x increases to the right, y increases upward.")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Tables and summaries
    # ------------------------------------------------------------------ #
    def render_status(self, tick: int, funds: int, riders: Sequence) -> str:
        """Return a snapshot of funds, riders and their orders."""
        lines = [f"Tick: {tick}", f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders on duty)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id:>2} | pos ({rider.x:>3},{rider.y:>3}) | "
                f"{rider.state_name:<11} | speed {rider.speed:>3} | "
                f"orders {len(order_ids)} {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Return a table with the details of every order."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Taken':>6} {'Rider':>6} Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            restaurant = f"({o.restaurant_x},{o.restaurant_y})"
            customer = f"({o.customer_x},{o.customer_y})"
            rider = "-" if o.rider_id is None else str(o.rider_id)
            taken = "-" if o.time_taken is None else str(o.time_taken)
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{o.distance:>9.0f} {taken:>6} {rider:>6} {o.status}"
            )
        return "\n".join(lines)

    def render_rider_events(self, riders: Sequence) -> str:
        """Return every recorded status change for all riders, in time order."""
        entries = []
        for rider in riders:
            entries.extend(rider.log)
        if not entries:
            return "No rider events recorded."
        entries.sort(key=lambda e: (e["tick"], e["rider_id"]))
        lines = []
        for e in entries:
            order = "-" if e["order_id"] is None else str(e["order_id"])
            lines.append(
                f"t={e['tick']:>4} Rider {e['rider_id']:>2} {e['event']:<22} "
                f"order {order:>4} at ({e['x']:>3},{e['y']:>3}) "
                f"state={STATE_NAMES.get(e['state'], '?')}"
            )
        return "\n".join(lines)

    def render_route_summary(self, order, rider, route: Sequence[Point]) -> str:
        """Return speed, distance and estimated time for an assigned route."""
        total = PathPlanner.route_length(route)
        eta = math.ceil(total / rider.speed) if rider.speed > 0 else 0
        return (f"Route for rider {rider.rider_id}: speed {rider.speed} units/tick, "
                f"total length {total} units, estimated time {eta} ticks "
                f"(order {order.id}).")
