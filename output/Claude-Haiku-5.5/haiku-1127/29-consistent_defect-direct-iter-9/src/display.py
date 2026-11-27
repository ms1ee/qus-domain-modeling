"""Status displays and ASCII map visualisation."""

from order_model import COMPLETED
from path_planner import MAP_SIZE, CELL_SIZE
from rider import STATE_NAMES

SCALE = 50                          # map units per character column/row
MAP_CHARS = MAP_SIZE // SCALE + 1   # 17 characters per axis (9 intersections)

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"

MAP_LEGEND = ("Legend: R rider  S restaurant  C customer  "
              ". intersection  # street  * planned route")


def _to_col(x):
    """Convert a map X coordinate to a character column."""
    return int(round(x / SCALE))


def _to_row(y):
    """Convert a map Y coordinate to a character row (north at the top)."""
    return int(round((MAP_SIZE - y) / SCALE))


class DisplayManager:
    """Builds text output for status, orders, rider logs and the map."""

    def render_map(self, riders=(), active_orders=(), route=None):
        """Render the street map as an ASCII string.

        Args:
            riders: Riders to draw as 'R'.
            active_orders: Orders whose restaurants ('S') and customers ('C')
                are drawn.
            route: Optional list of ``(x, y)`` points drawn as '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        grid = [[" "] * MAP_CHARS for _ in range(MAP_CHARS)]
        for row in range(MAP_CHARS):
            for col in range(MAP_CHARS):
                if row % 2 == 0 and col % 2 == 0:
                    grid[row][col] = SYMBOL_EMPTY
                elif row % 2 == 0 or col % 2 == 0:
                    grid[row][col] = SYMBOL_STREET

        if route:
            for start, end in zip(route, route[1:]):
                self._draw_segment(grid, start, end, SYMBOL_ROUTE)
            if route:
                self._plot(grid, route[0], SYMBOL_ROUTE)

        for order in active_orders:
            if order.status == COMPLETED:
                continue
            self._plot(grid, order.restaurant, SYMBOL_RESTAURANT)
            self._plot(grid, order.customer, SYMBOL_CUSTOMER)

        for rider in riders:
            self._plot(grid, rider.position, SYMBOL_RIDER)

        lines = ["".join(row) for row in grid]
        lines.append(MAP_LEGEND)
        return "\n".join(lines)

    def render_status(self, funds, riders, pending_count):
        """Render the system status snapshot.

        Args:
            funds: Current fund balance.
            riders: List of Rider objects.
            pending_count: Number of orders waiting for a rider.

        Returns:
            Multi-line status string.
        """
        idle = sum(1 for rider in riders if rider.state == 0)
        lines = [
            f"System funds: {funds}",
            f"Riders: {len(riders)} (idle: {idle})   Pending orders: {pending_count}",
        ]
        if not riders:
            lines.append("  No riders on duty.")
        for rider in riders:
            active = [o for o in rider.orders if o.status != COMPLETED]
            order_text = ", ".join(f"#{o.id}({o.status})" for o in active) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: location=({rider.x}, {rider.y}) "
                f"status={STATE_NAMES[rider.state]} speed={rider.speed} "
                f"active orders={len(active)} [{order_text}]"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render the order table with timing and distance details.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line table string.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = [
            f"{'ID':<5}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
            f"{'Dist':<7}{'Taken':<7}{'Eff':<7}{'Rider':<7}Status"
        ]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            eff = "-" if order.efficiency is None else str(order.efficiency)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:<5}{order.start_time:<7}"
                f"{str(order.restaurant):<13}{str(order.customer):<13}"
                f"{order.distance:<7}{taken:<7}{eff:<7}{rider:<7}{order.status}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render every recorded status change for all riders.

        Args:
            riders: List of Rider objects.

        Returns:
            Multi-line log string.
        """
        if not riders:
            return "No riders on duty."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  [t={entry['time']:>4}] {entry['event']:<22} "
                    f"order={order_text:<5} at ({entry['x']}, {entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], entry['state'])}"
                )
        return "\n".join(lines)

    def _plot(self, grid, point, symbol):
        """Place ``symbol`` at the character cell corresponding to ``point``."""
        row = _to_row(point[1])
        col = _to_col(point[0])
        if 0 <= row < MAP_CHARS and 0 <= col < MAP_CHARS:
            grid[row][col] = symbol

    def _draw_segment(self, grid, start, end, symbol):
        """Draw an axis-aligned route segment with ``symbol``."""
        dist = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        steps = max(1, dist // 10)
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            self._plot(grid, (x, y), symbol)
