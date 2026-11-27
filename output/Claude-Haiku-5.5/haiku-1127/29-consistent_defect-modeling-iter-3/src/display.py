"""Status display and ASCII map rendering.

The ASCII map shows the 8x8 street grid (800x800 units) using 17 characters
per side: every 100 units is two characters apart, with the street characters
'#' on the grid lines and '.' for the cell interiors. Symbols:
    R  rider          S  restaurant       C  customer
    #  street         .  empty cell space *  planned route
"""

from path_planner import MAP_SIZE
from rider import STATE_NAMES

CANVAS_SIZE = 17
STEPS = CANVAS_SIZE - 1


class DisplayManager:
    """Renders system status, order tables, logs and the ASCII map.

    Attributes:
        map_size (int): Map size in units (800).
    """

    def __init__(self, map_size=MAP_SIZE):
        """Create a display manager.

        Args:
            map_size: Map size in coordinate units.
        """
        self.map_size = map_size

    def to_char(self, x, y):
        """Convert a map coordinate to a ``(row, col)`` canvas index."""
        col = round(x * STEPS / self.map_size)
        row = round(y * STEPS / self.map_size)
        col = min(max(col, 0), STEPS)
        row = min(max(row, 0), STEPS)
        return row, col

    def _base_grid(self):
        """Return an empty canvas with streets and cell interiors."""
        return [
            ["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(CANVAS_SIZE)]
            for r in range(CANVAS_SIZE)
        ]

    def _put(self, grid, point, symbol):
        """Place ``symbol`` at the canvas position of a map point."""
        row, col = self.to_char(point[0], point[1])
        grid[row][col] = symbol

    def _draw_segment(self, grid, start, end):
        """Draw a route segment with '*' over street and empty characters."""
        r1, c1 = self.to_char(start[0], start[1])
        r2, c2 = self.to_char(end[0], end[1])
        if r1 == r2:
            cells = [(r1, c) for c in range(min(c1, c2), max(c1, c2) + 1)]
        elif c1 == c2:
            cells = [(r, c1) for r in range(min(r1, r2), max(r1, r2) + 1)]
        else:  # pragma: no cover - routes are always axis-aligned
            return
        for row, col in cells:
            if grid[row][col] in "#.":
                grid[row][col] = "*"

    def render_map(self, riders=(), orders=(), route=None):
        """Render the ASCII map with riders, active orders and an optional route.

        Args:
            riders: Iterable of riders to mark with 'R'.
            orders: Iterable of orders; active ones show 'S' and 'C'.
            route: Optional list of waypoints drawn as connected segments.

        Returns:
            Multi-line string of the map.
        """
        grid = self._base_grid()
        if route:
            for start, end in zip(route, route[1:]):
                self._draw_segment(grid, start, end)
        for order in orders:
            if order.status == "completed":
                continue
            self._put(grid, order.res_pos, "S")
            self._put(grid, order.cus_pos, "C")
        for rider in riders:
            self._put(grid, (rider.x, rider.y), "R")

        lines = []
        for row_index, row in enumerate(grid):
            if row_index % 2 == 0:
                label = f"{row_index * self.map_size // STEPS:>4} "
            else:
                label = "     "
            lines.append(label + "".join(row))
        lines.append("     x: 0 .. 800 (left to right), y: 0 .. 800 (top to bottom)")
        lines.append("Legend: R rider, S restaurant, C customer, # street, "
                     ". cell interior, * route")
        return "\n".join(lines)

    def render_status(self, system):
        """Return a text snapshot of funds, riders and pending orders.

        Args:
            system: The ``SystemManager`` instance.
        """
        riders = system.riders
        lines = [
            f"System funds: {system.funds}",
            f"Simulation tick: {system.current_tick}",
            f"Riders: {len(riders)}",
            f"Pending orders: {len(system.order_manager.pending_orders())}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={rider.state_name} active orders={len(rider.active_orders())} "
                f"order list={order_ids}"
            )
        issues = system.check_consistency()
        if issues:
            lines.append("Consistency issues:")
            lines.extend(f"  - {issue}" for issue in issues)
        else:
            lines.append("Consistency: OK")
        return "\n".join(lines)

    def render_orders(self, orders):
        """Return a table of order details.

        Args:
            orders: Iterable of ``Order`` objects.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Distance':>9} {'Taken':>6} {'Rider':>6} {'Status':>10}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>9.0f} {taken:>6} {rider:>6} {order.status:>10}"
            )
            if order.efficiency() is not None:
                lines.append(f"      delivery efficiency: {order.efficiency():.2f} units/tick")
        return "\n".join(lines)

    def format_log_entry(self, rider, entry):
        """Return one formatted rider log line.

        Args:
            rider: The ``Rider`` that produced the entry.
            entry: A dictionary from ``rider.log``.
        """
        order_text = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
        state = STATE_NAMES.get(entry["state"], "unknown")
        return (
            f"[tick {entry['tick']:>4}] Rider #{rider.rider_id} "
            f"{entry['event']:<22} order={order_text:<6} "
            f"at ({entry['x']}, {entry['y']}) state={state}"
        )

    def render_rider_logs(self, riders):
        """Return the full status-change history of every rider.

        Args:
            riders: Iterable of ``Rider`` objects.
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}, "
                         f"status {rider.state_name}):")
            for entry in rider.log:
                lines.append("  " + self.format_log_entry(rider, entry))
        return "\n".join(lines)
