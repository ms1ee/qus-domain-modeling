"""Status display and ASCII map rendering."""

from path_planner import MAP_SIZE, CELL_SIZE, GRID_SIZE
from order_model import STATUS_COMPLETED
from rider import STATE_NAMES


class DisplayManager:
    """Renders status text, tables and the ASCII map.

    Attributes:
        map_width (int): Number of cells horizontally.
        map_height (int): Number of cells vertically.
    """

    def __init__(self, map_width=GRID_SIZE, map_height=GRID_SIZE):
        """Create a display manager.

        Args:
            map_width: Number of cells horizontally.
            map_height: Number of cells vertically.
        """
        self.map_width = map_width
        self.map_height = map_height

    @staticmethod
    def _to_canvas(x, y):
        """Convert map coordinates to ``(row, col)`` canvas indices.

        Intersections land on even rows and columns; street segments between
        them land on odd indices; blocks land on odd row and odd column.
        """
        col = int(round(x * 2 / CELL_SIZE))
        row = int(round((MAP_SIZE - y) * 2 / CELL_SIZE))
        return row, col

    def render_riders(self, riders):
        """Return a table describing every rider."""
        if not riders:
            return "No riders recruited yet."
        lines = ["Riders:"]
        for rider in riders:
            orders = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider {rider.rider_id:>3} | pos ({rider.x:>3}, {rider.y:>3}) | "
                f"state: {STATE_NAMES.get(rider.state, 'unknown'):<10} | "
                f"speed: {rider.speed} | orders: {len(rider.orders)} [{orders}]"
            )
        return "\n".join(lines)

    def render_status(self, system):
        """Return a snapshot of funds, riders and order lists."""
        active = system.active_orders()
        lines = [
            f"Simulated time : {system.simulated_time}",
            f"System funds   : {system.funds}",
            f"Riders         : {len(system.riders)} (max {system.max_riders})",
            f"Recruit cost   : {system.rider_recruitment_cost}",
            f"Active orders  : {len(active)}",
            self.render_riders(system.riders),
        ]
        return "\n".join(lines)

    def render_orders(self, orders):
        """Return a table with details for all orders."""
        if not orders:
            return "No orders yet."
        lines = ["Orders:"]
        for o in orders:
            rider = f"rider {o.rider_id}" if o.rider_id is not None else "unassigned"
            done = o.time_taken if o.time_taken is not None else "-"
            lines.append(
                f"  #{o.id:<4} | start t={o.start_time:<5} | "
                f"restaurant ({o.restaurant_x}, {o.restaurant_y}) | "
                f"customer ({o.customer_x}, {o.customer_y}) | "
                f"distance {o.distance:<4} | time taken {done} | "
                f"{rider} | {o.status}"
            )
        return "\n".join(lines)

    def render_map(self, riders, orders, route=None):
        """Render the ASCII map with streets, orders, riders and an optional route.

        Symbols: ``+`` intersection, ``-``/``|`` street, ``*`` route,
        ``R`` restaurant, ``C`` customer, ``O`` rider, blank space for blocks.

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant/customer locations are drawn.
            route: Optional list of ``(x, y)`` waypoints to highlight.

        Returns:
            Multi-line string with the map and a legend.
        """
        rows = 2 * self.map_height + 1
        cols = 2 * self.map_width + 1
        canvas = [[" "] * cols for _ in range(rows)]

        for gy in range(self.map_height + 1):
            for gx in range(self.map_width + 1):
                r, c = self._to_canvas(gx * CELL_SIZE, gy * CELL_SIZE)
                canvas[r][c] = "+"
                if gx < self.map_width:
                    canvas[r][c + 1] = "-"
                if gy < self.map_height:
                    canvas[r + 1][c] = "|"

        if route:
            for a, b in zip(route, route[1:]):
                r1, c1 = self._to_canvas(*a)
                r2, c2 = self._to_canvas(*b)
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        canvas[r][c] = "*"

        def put(x, y, symbol):
            r, c = self._to_canvas(x, y)
            if 0 <= r < rows and 0 <= c < cols:
                canvas[r][c] = symbol

        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            put(order.restaurant_x, order.restaurant_y, "R")
            put(order.customer_x, order.customer_y, "C")
        for rider in riders:
            put(rider.x, rider.y, "O")

        lines = []
        for r, row in enumerate(canvas):
            if r % 2 == 0:
                y_value = MAP_SIZE - (r // 2) * CELL_SIZE
                label = f"{y_value:>4} "
            else:
                label = "     "
            lines.append(label + "".join(row).rstrip())
        lines.append("     x: 0 (left) .. 800 (right); y: 0 (bottom) .. 800 (top)")
        lines.append("Legend: + intersection  -/| street  * route  "
                     "R restaurant  C customer  O rider")
        return "\n".join(lines)
