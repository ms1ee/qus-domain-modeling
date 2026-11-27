"""Status displays and ASCII map rendering.

The map is drawn as a 17x17 character canvas. Even rows and columns hold the
street intersections (multiples of 100 units); odd positions hold street
segments. Symbols:
    +  intersection      -  horizontal street   |  vertical street
    .  block (empty)     *  planned route       M  restaurant
    C  customer          @  rider
"""

import math

from config import CELL_SIZE, GRID_SIZE
from path_planner import PathPlanner
from rider import STATE_NAMES

HALF_CELL = CELL_SIZE // 2
SYMBOL_INTERSECTION = "+"
SYMBOL_HORIZONTAL = "-"
SYMBOL_VERTICAL = "|"
SYMBOL_EMPTY = "."
SYMBOL_ROUTE = "*"
SYMBOL_RESTAURANT = "M"
SYMBOL_CUSTOMER = "C"
SYMBOL_RIDER = "@"

LEGEND = (
    "Legend: + intersection  - | street  . block  * route  "
    "M restaurant  C customer  @ rider"
)


class DisplayManager:
    """Render the map, status snapshots, order tables and rider logs."""

    def __init__(self):
        """Create a display manager sized for the configured grid."""
        self.size = GRID_SIZE // HALF_CELL + 1

    def _new_canvas(self):
        """Return an empty street canvas as a list of character lists."""
        canvas = []
        for row in range(self.size):
            line = []
            for col in range(self.size):
                if row % 2 == 0 and col % 2 == 0:
                    char = SYMBOL_INTERSECTION
                elif row % 2 == 0:
                    char = SYMBOL_HORIZONTAL
                elif col % 2 == 0:
                    char = SYMBOL_VERTICAL
                else:
                    char = SYMBOL_EMPTY
                line.append(char)
            canvas.append(line)
        return canvas

    def _to_cell(self, x, y):
        """Convert map coordinates to canvas ``(row, col)``; y grows upward."""
        col = min(max(int(x) // HALF_CELL, 0), self.size - 1)
        row = min(max((GRID_SIZE - int(y)) // HALF_CELL, 0), self.size - 1)
        return row, col

    def _draw_route(self, canvas, nodes):
        """Draw a connected route of lattice nodes onto the canvas."""
        cells = [self._to_cell(x, y) for x, y in nodes]
        for index, (row, col) in enumerate(cells):
            canvas[row][col] = SYMBOL_ROUTE
            if index > 0:
                prev_row, prev_col = cells[index - 1]
                mid_row = (prev_row + row) // 2
                mid_col = (prev_col + col) // 2
                canvas[mid_row][mid_col] = SYMBOL_ROUTE

    def render_map(self, riders=(), orders=(), routes=()):
        """Render the ASCII map.

        Args:
            riders: Riders to mark with ``@``.
            orders: Orders whose restaurant (M) and customer (C) locations
                are marked; completed orders are skipped.
            routes: Node lists to draw as connected route lines.

        Returns:
            str: Multi-line map text including a legend.
        """
        canvas = self._new_canvas()
        for route in routes:
            if len(route) >= 1:
                self._draw_route(canvas, route)
        for order in orders:
            if order.is_completed():
                continue
            row, col = self._to_cell(*order.res_pos)
            canvas[row][col] = SYMBOL_RESTAURANT
            row, col = self._to_cell(*order.cus_pos)
            canvas[row][col] = SYMBOL_CUSTOMER
        for rider in riders:
            row, col = self._to_cell(rider.x, rider.y)
            canvas[row][col] = SYMBOL_RIDER
        lines = ["".join(row) for row in canvas]
        return "\n".join(lines) + "\n" + LEGEND

    def render_status(self, funds, tick, riders):
        """Render the system status snapshot.

        Args:
            funds: Current fund balance.
            tick: Current simulated time.
            riders: List of riders.

        Returns:
            str: Status text.
        """
        lines = [
            f"Funds: {funds}",
            f"Tick: {tick}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders] or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x},{rider.y}) "
                f"state={rider.state_name} speed={rider.speed} "
                f"orders={order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of all orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>5} {'Taken':>6} {'Eff':>6} {'Rider':>6} {'Status':<10}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = order.time_taken
            eff = order.efficiency
            rider = order.rider_id if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.created_tick:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>5} {'-' if taken is None else taken:>6} "
                f"{'-' if eff is None else eff:>6} {str(rider):>6} "
                f"{order.status:<10}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render the status-change history of every rider.

        Args:
            riders: List of riders.

        Returns:
            str: Log text grouped by rider.
        """
        if not riders:
            return "No riders."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} log:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = entry["order_id"] if entry["order_id"] is not None else "-"
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:>4} {entry['event']:<20} "
                    f"order={order!s:<4} at ({entry['x']},{entry['y']}) "
                    f"state={state}"
                )
        return "\n".join(lines)

    def render_route(self, rider, order=None):
        """Render the route map and summary for a rider.

        Args:
            rider: The rider whose planned route is drawn.
            order: Optional order whose restaurant and customer are marked.

        Returns:
            str: Map followed by a speed/time summary.
        """
        nodes = rider.route_nodes()
        orders = [order] if order is not None else []
        map_text = self.render_map(riders=[rider], orders=orders, routes=[nodes])
        length = PathPlanner.route_length(nodes[1:], start=nodes[0])
        if rider.speed > 0:
            ticks = math.ceil(length / rider.speed) if length else 0
        else:
            ticks = 0
        summary = (
            f"Route for rider #{rider.rider_id}: speed {rider.speed} units/tick, "
            f"route length {length} units, estimated time {ticks} tick(s)."
        )
        return map_text + "\n" + summary
