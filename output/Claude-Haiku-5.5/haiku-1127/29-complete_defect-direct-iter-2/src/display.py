"""Presentation helpers: ASCII map, status tables and log listings.

The ASCII map samples the 800x800 plane every 50 units, giving a 17x17
character canvas. Even canvas indices lie on street lines and odd indices are
cell interiors. Symbols: R rider, S restaurant, C customer, # street,
. empty cell, * route.
"""

from config import CELL_SIZE, MAP_SIZE
from order_model import STATUS_COMPLETED
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"

CHAR_STEP = CELL_SIZE // 2
CANVAS_SIZE = MAP_SIZE // CHAR_STEP + 1


class DisplayManager:
    """Builds text output for the command-line interface."""

    @staticmethod
    def _to_index(value):
        """Convert a coordinate to a canvas index.

        Args:
            value: Coordinate in units.

        Returns:
            Index clamped to 0..CANVAS_SIZE-1.
        """
        index = int(round(value / CHAR_STEP))
        return min(max(index, 0), CANVAS_SIZE - 1)

    @staticmethod
    def _blank_canvas():
        """Return a canvas with streets and empty cells.

        Returns:
            Two-dimensional list of symbols indexed as ``canvas[row][col]``.
        """
        return [
            [SYMBOL_STREET if (row % 2 == 0 or col % 2 == 0)
             else SYMBOL_EMPTY for col in range(CANVAS_SIZE)]
            for row in range(CANVAS_SIZE)
        ]

    @staticmethod
    def _mark_route(canvas, col, row):
        """Mark a canvas cell as route if it is empty or street.

        Args:
            canvas: The canvas to modify.
            col: Column index.
            row: Row index.
        """
        if canvas[row][col] in (SYMBOL_EMPTY, SYMBOL_STREET):
            canvas[row][col] = SYMBOL_ROUTE

    def _draw_route(self, canvas, points):
        """Draw connected segments of a route onto the canvas.

        Args:
            canvas: The canvas to modify.
            points: List of ``(x, y)`` points, starting with the rider.
        """
        for start, end in zip(points, points[1:]):
            s_col, s_row = self._to_index(start[0]), self._to_index(start[1])
            e_col, e_row = self._to_index(end[0]), self._to_index(end[1])
            if s_col == e_col:
                for row in range(min(s_row, e_row), max(s_row, e_row) + 1):
                    self._mark_route(canvas, s_col, row)
            elif s_row == e_row:
                for col in range(min(s_col, e_col), max(s_col, e_col) + 1):
                    self._mark_route(canvas, col, s_row)
            else:
                self._mark_route(canvas, s_col, s_row)
                self._mark_route(canvas, e_col, e_row)
        if points:
            self._mark_route(canvas, self._to_index(points[0][0]),
                             self._to_index(points[0][1]))

    def _place(self, canvas, point, symbol):
        """Place a symbol at a map point.

        Args:
            canvas: The canvas to modify.
            point: Tuple ``(x, y)``.
            symbol: Character to place.
        """
        col = self._to_index(point[0])
        row = self._to_index(point[1])
        canvas[row][col] = symbol

    def render_map(self, riders=(), orders=(), route=None):
        """Render the ASCII map.

        Args:
            riders: Riders to draw as R.
            orders: Orders whose restaurant (S) and customer (C) points are
                drawn if not completed.
            route: Optional list of ``(x, y)`` points to draw as a connected
                route graph.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = self._blank_canvas()
        if route:
            self._draw_route(canvas, route)
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            self._place(canvas, order.res_pos, SYMBOL_RESTAURANT)
            self._place(canvas, order.cus_pos, SYMBOL_CUSTOMER)
        for rider in riders:
            self._place(canvas, rider.position, SYMBOL_RIDER)

        lines = ["Map: 800x800 units, 8x8 cells of 100 units "
                 "(1 character = 50 units)"]
        for row in reversed(range(CANVAS_SIZE)):
            label = f"{row * CHAR_STEP:>4}" if row % 2 == 0 else "    "
            lines.append(f"{label} " + " ".join(canvas[row]))
        lines.append("Legend: R rider, S restaurant, C customer, "
                     "# street, . empty, * route")
        return "\n".join(lines)

    @staticmethod
    def render_status(funds, tick, riders, pending_count):
        """Render the system status snapshot.

        Args:
            funds: Current fund balance.
            tick: Current simulated tick.
            riders: List of riders.
            pending_count: Number of orders waiting for a rider.

        Returns:
            Multi-line status string.
        """
        lines = [f"System status at tick {tick}",
                 f"Funds: {funds}",
                 f"Riders: {len(riders)} (pending orders: {pending_count})"]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} pos=({rider.x},{rider.y}) "
                f"state={STATE_NAMES.get(rider.state, '?'):<11} "
                f"speed={rider.speed} "
                f"orders={order_ids if order_ids else 'none'} "
                f"special_case={'yes' if rider.special_case else 'no'}")
        return "\n".join(lines)

    @staticmethod
    def render_orders(orders):
        """Render a table of all orders.

        Args:
            orders: List of Order objects.

        Returns:
            Multi-line table string.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>6} {'Time':>6} "
                  f"{'Eff/tick':>9} {'Rider':>6} {'Status':<12}")
        lines = [header, "-" * len(header)]
        for order in orders:
            elapsed = order.time_taken()
            efficiency = order.efficiency()
            rider = f"#{order.rider_id}" if order.rider_id else "-"
            lines.append(
                f"{order.id:>4} {order.start_tick:>6} "
                f"{str(order.raw_restaurant):>12} "
                f"{str(order.raw_customer):>12} {order.distance:>6} "
                f"{(str(elapsed) if elapsed is not None else '-'):>6} "
                f"{(f'{efficiency:.2f}' if efficiency is not None else '-'):>9}"
                f" {rider:>6} {order.status:<12}")
        return "\n".join(lines)

    @staticmethod
    def render_rider_logs(riders):
        """Render the status-change history of every rider.

        Args:
            riders: List of Rider objects.

        Returns:
            Multi-line string of log records.
        """
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order = (f"order #{entry['order_id']}"
                         if entry["order_id"] is not None else "-")
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<20} | "
                    f"{order:<10} | pos ({entry['x']},{entry['y']}) | "
                    f"state {STATE_NAMES.get(entry['state'], '?')}")
        return "\n".join(lines)

    @staticmethod
    def render_route_summary(rider, order, length, ticks, queued):
        """Render the route summary shown after an order is placed.

        Args:
            rider: The assigned Rider.
            order: The new Order.
            length: Estimated route length in units.
            ticks: Estimated ticks to finish the route.
            queued: Number of earlier orders ahead of this one.

        Returns:
            Multi-line summary string.
        """
        lines = [
            f"Assigned rider #{rider.rider_id} to order #{order.id}",
            f"  Speed: {rider.speed} units/tick",
            f"  Estimated route length: {length} units",
            f"  Estimated time: {ticks} tick(s)",
        ]
        if queued:
            lines.append(f"  Queued behind {queued} earlier order(s); the "
                         "route shown starts from the rider's current "
                         "position.")
        return "\n".join(lines)
