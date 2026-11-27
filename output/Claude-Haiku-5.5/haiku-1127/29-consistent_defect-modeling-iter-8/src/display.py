"""Status reports, order/rider tables and ASCII map rendering."""

from path_planner import CELL_SIZE, GRID_DIMENSION
from rider import STATE_NAMES
import globalvar

CANVAS_STEP = CELL_SIZE // 2  # each canvas character covers 50 units


class DisplayManager:
    """Produces text output for the command-line interface."""

    def __init__(self, system, map_dimension=GRID_DIMENSION):
        """Create a display bound to the system manager.

        Args:
            system: The SystemManager whose state is displayed.
            map_dimension: Number of grid cells per side (8).
        """
        self.system = system
        self.map_dimension = map_dimension

    def status_report(self):
        """Return the system status snapshot as text."""
        riders = self.system.riders
        lines = [
            "=== System Status ===",
            f"System funds: {self.system.funds}",
            f"Current tick: {globalvar.current_tick()}",
            f"Riders: {len(riders)} (idle: {len(self.system.idle_riders())})",
        ]
        if not riders:
            lines.append("No riders on duty.")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: location ({rider.x}, {rider.y}), "
                f"status {rider.state_name()}, active orders "
                f"{rider.active_order_count()}, order list {order_ids or '-'}"
            )
        return "\n".join(lines)

    def orders_report(self, orders):
        """Return a table of order details.

        Args:
            orders: Iterable of Order objects.
        """
        orders = list(orders)
        if not orders:
            return "No orders."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{f'({order.restaurant_x},{order.restaurant_y})':>12} "
                f"{f'({order.customer_x},{order.customer_y})':>12} "
                f"{order.distance:>6} {taken:>6} {rider:>6} {order.status:>12}"
            )
        return "\n".join(lines)

    def riders_report(self):
        """Return every recorded status change for all riders."""
        riders = self.system.riders
        if not riders:
            return "No riders on duty."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (current state: {rider.state_name()})")
            for entry in rider.log:
                order_id = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} order {order_id:<6} "
                    f"at ({entry['x']}, {entry['y']})"
                )
        return "\n".join(lines)

    def _mark(self, canvas, x, y, symbol):
        """Place ``symbol`` on the canvas at map coordinates (x, y)."""
        size = len(canvas)
        row = min(max(y // CANVAS_STEP, 0), size - 1)
        col = min(max(x // CANVAS_STEP, 0), size - 1)
        canvas[row][col] = symbol

    def _draw_segment(self, canvas, start, end, symbol):
        """Draw an axis-aligned route segment on the canvas."""
        size = len(canvas)
        ar = min(max(start[1] // CANVAS_STEP, 0), size - 1)
        ac = min(max(start[0] // CANVAS_STEP, 0), size - 1)
        br = min(max(end[1] // CANVAS_STEP, 0), size - 1)
        bc = min(max(end[0] // CANVAS_STEP, 0), size - 1)
        for row in range(min(ar, br), max(ar, br) + 1):
            for col in range(min(ac, bc), max(ac, bc) + 1):
                canvas[row][col] = symbol

    def map_text(self, orders=None, route=None):
        """Render the ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street,
        '.' empty block, '*' planned route.

        Args:
            orders: Optional iterable of orders whose S/C points and status
                are displayed.
            route: Optional list of waypoints drawn as connected segments.

        Returns:
            Multi-line string of the map and a short order status list.
        """
        size = self.map_dimension * 2 + 1
        canvas = [
            ['#' if (r % 2 == 0 or c % 2 == 0) else '.' for c in range(size)]
            for r in range(size)
        ]
        if route:
            if len(route) == 1:
                self._mark(canvas, route[0][0], route[0][1], '*')
            for start, end in zip(route, route[1:]):
                self._draw_segment(canvas, start, end, '*')
        orders = list(orders or [])
        for order in orders:
            self._mark(canvas, order.restaurant_x, order.restaurant_y, 'S')
            self._mark(canvas, order.customer_x, order.customer_y, 'C')
        for rider in self.system.riders:
            self._mark(canvas, rider.x, rider.y, 'R')

        lines = ["".join(row) for row in canvas]
        lines.append("Legend: R rider, S restaurant, C customer, # street, "
                     ". block, * route (1 char = 50 units, origin top-left)")
        for order in orders:
            lines.append(
                f"Order #{order.id}: S({order.restaurant_x},{order.restaurant_y}) -> "
                f"C({order.customer_x},{order.customer_y}) [{order.status}]"
            )
        return "\n".join(lines)
