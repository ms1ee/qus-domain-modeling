"""Status displays and ASCII map visualisation for the terminal."""

import logging

from path_planner import CELL_SIZE, GRID_SIZE, MAP_SIZE, PathPlanner, route_length
from rider import DELIVERING, IDLE, PICKING_UP

logger = logging.getLogger(__name__)

UNIT = CELL_SIZE // 2
CANVAS_SIZE = GRID_SIZE * 2 + 1
SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "M"
SYMBOL_CUSTOMER = "C"
SYMBOL_ROUTE = "*"
SYMBOL_MARKERS = (SYMBOL_RIDER, SYMBOL_RESTAURANT, SYMBOL_CUSTOMER)
LEGEND = ("Legend: R=rider  M=restaurant  C=customer  "
          "-,|,+=streets  .=cell center  *=route  (x,y: 0-800, y grows downward)")


def point_to_canvas(x, y):
    """Convert a map point into ``(row, col)`` on the 17x17 canvas.

    Each canvas cell represents 50x50 map units, so intersections sit on even
    rows/columns and cell centers on odd rows/columns.
    """
    col = min(max(int(x) // UNIT, 0), CANVAS_SIZE - 1)
    row = min(max(int(y) // UNIT, 0), CANVAS_SIZE - 1)
    return row, col


def _line_cells(a, b):
    """Return canvas cells on a straight (or near-straight) line from a to b."""
    (r0, c0), (r1, c1) = a, b
    steps = max(abs(r1 - r0), abs(c1 - c0))
    cells = []
    for k in range(steps + 1):
        if steps:
            r = r0 + (r1 - r0) * k // steps
            c = c0 + (c1 - c0) * k // steps
        else:
            r, c = r0, c0
        cells.append((r, c))
    return cells


class DisplayManager:
    """Renders the system status, order and rider tables and the ASCII map."""

    @staticmethod
    def blank_canvas():
        """Return the empty street grid as a list of character rows."""
        canvas = []
        for row in range(CANVAS_SIZE):
            line = []
            for col in range(CANVAS_SIZE):
                if row % 2 == 0 and col % 2 == 0:
                    char = "+"
                elif row % 2 == 0:
                    char = "-"
                elif col % 2 == 0:
                    char = "|"
                else:
                    char = "."
                line.append(char)
            canvas.append(line)
        return canvas

    @staticmethod
    def _stamp(canvas, point, symbol):
        """Place ``symbol`` on the canvas at the cell that contains ``point``."""
        row, col = point_to_canvas(point[0], point[1])
        canvas[row][col] = symbol

    @staticmethod
    def _draw_route(canvas, start, points):
        """Draw a connected line segment graph through ``points`` with ``*``."""
        previous = start
        for point in points:
            r0, c0 = point_to_canvas(*previous)
            r1, c1 = point_to_canvas(*point)
            for r, c in _line_cells((r0, c0), (r1, c1)):
                if canvas[r][c] not in SYMBOL_MARKERS:
                    canvas[r][c] = SYMBOL_ROUTE
            previous = point

    @staticmethod
    def _render_canvas(canvas):
        """Convert the canvas into text lines with y-axis labels."""
        lines = [f"Map: x 0..{MAP_SIZE} (left to right), y 0..{MAP_SIZE} (top to bottom)"]
        for row_index, row in enumerate(canvas):
            label = f"{row_index * UNIT:>4} " if row_index % 2 == 0 else "     "
            lines.append(label + "".join(row))
        return "\n".join(lines)

    def render_map(self, riders=None, orders=None):
        """Render the current map with riders and active orders.

        Args:
            riders: Iterable of riders to show.
            orders: Iterable of orders; completed orders are hidden.

        Returns:
            Multi-line string containing the ASCII map and legend.
        """
        canvas = self.blank_canvas()
        for order in orders or []:
            if order.status == "completed":
                continue
            self._stamp(canvas, order.res_pos, SYMBOL_RESTAURANT)
            self._stamp(canvas, order.cus_pos, SYMBOL_CUSTOMER)
        for rider in riders or []:
            self._stamp(canvas, rider.position, SYMBOL_RIDER)
        return self._render_canvas(canvas) + "\n" + LEGEND

    def render_route(self, rider, order):
        """Render the route a rider will take to serve ``order``.

        Includes the rider speed and an estimated number of ticks, and draws the
        route on the ASCII map.

        Args:
            rider: The assigned :class:`rider.Rider`.
            order: The :class:`order_model.Order`.

        Returns:
            Multi-line description and map string.
        """
        planner = PathPlanner()
        if rider.state == DELIVERING:
            points = list(rider.waypoints)
        elif rider.state == PICKING_UP:
            points = list(rider.waypoints) + planner.plan(order.res_pos, order.cus_pos)
        else:
            points = planner.plan(rider.position, order.res_pos) + \
                planner.plan(order.res_pos, order.cus_pos)
        length = route_length(rider.position, points)
        speed = max(1, rider.speed)
        ticks = -(-length // speed) if length else 0

        canvas = self.blank_canvas()
        self._draw_route(canvas, rider.position, points)
        self._stamp(canvas, order.res_pos, SYMBOL_RESTAURANT)
        self._stamp(canvas, order.cus_pos, SYMBOL_CUSTOMER)
        self._stamp(canvas, rider.position, SYMBOL_RIDER)

        header = (
            f"Order #{order.id} assigned to Rider #{rider.rider_id} "
            f"(state: {rider.state_name})\n"
            f"Restaurant cell center: {order.res_pos}   "
            f"Customer cell center: {order.cus_pos}\n"
            f"Rider speed: {rider.speed} units/tick   "
            f"Route length: {length} units   "
            f"Estimated time: {ticks} tick(s)"
        )
        return header + "\n" + self._render_canvas(canvas) + "\n" + LEGEND

    @staticmethod
    def format_status(funds, riders, tick):
        """Format the system snapshot: funds, tick and each rider's state.

        Args:
            funds: Current fund balance.
            riders: Iterable of riders.
            tick: Current simulated tick.

        Returns:
            Multi-line string.
        """
        riders = list(riders or [])
        lines = [f"Tick: {tick} | System funds: {funds} | Riders: {len(riders)}"]
        if not riders:
            lines.append("No riders recruited yet.")
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} state={rider.state_name:<11} "
                f"pos=({rider.x},{rider.y}) speed={rider.speed} "
                f"orders={len(rider.orders)} {order_ids} "
                f"special={'yes' if rider.special_case else 'no'}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Format a table of order details.

        Args:
            orders: Iterable of orders.

        Returns:
            Multi-line string table.
        """
        orders = list(orders or [])
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Rider':>6} {'Status':<12} {'Dist':>6} {'Time':>6} {'Eff':>6}")
        lines = [header, "-" * len(header)]
        for order in orders:
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            taken = order.time_taken
            efficiency = order.efficiency()
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {str(order.res_pos):>12} "
                f"{str(order.cus_pos):>12} {rider:>6} {order.status:<12} "
                f"{order.distance:>6} {'-' if taken is None else taken:>6} "
                f"{'-' if efficiency is None else efficiency:>6}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """Format every status-change record of every rider.

        Args:
            riders: Iterable of riders.

        Returns:
            Multi-line string of log entries.
        """
        lines = []
        for rider in riders or []:
            lines.append(f"Rider #{rider.rider_id} log ({len(rider.log)} entries):")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:<5} {entry['event']:<22} order={order:<5} "
                    f"pos=({entry['x']},{entry['y']}) state={entry['state']}"
                )
        return "\n".join(lines) if lines else "No riders recruited yet."
