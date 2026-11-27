"""Status text and ASCII map rendering for the dispatch simulator.

The map is drawn on a 17x17 character canvas: one character represents 50
map units, so grid lines (multiples of 100) fall on even indices and cell
centers fall on odd indices. Symbols:

* ``R`` rider, ``S`` restaurant, ``C`` customer, ``.`` empty cell center,
  ``#`` street, ``*`` planned route.
"""

import logging

from grid_map import CELL_SIZE, MAP_SIZE
from rider import STATE_NAMES

logger = logging.getLogger(__name__)

SCALE = 50
CANVAS_SIZE = MAP_SIZE // SCALE + 1


class DisplayManager:
    """Formats monitoring output and renders the command-line map.

    Attributes:
        map_symbol_rider: Character for riders.
        map_symbol_restaurant: Character for restaurants.
        map_symbol_customer: Character for customers.
        map_symbol_empty: Character for empty cell centers.
        map_symbol_street: Character for streets.
        map_symbol_route: Character for planned routes.
    """

    def __init__(self):
        """Create a display manager with the standard symbols."""
        self.map_symbol_rider = "R"
        self.map_symbol_restaurant = "S"
        self.map_symbol_customer = "C"
        self.map_symbol_empty = "."
        self.map_symbol_street = "#"
        self.map_symbol_route = "*"

    @staticmethod
    def _index(value):
        """Convert a map coordinate to a canvas index."""
        return max(0, min(CANVAS_SIZE - 1, value // SCALE))

    def render_map(self, riders, orders, route_waypoints=None):
        """Render the 8x8 grid with riders, active orders and an optional route.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects; completed orders are skipped.
            route_waypoints: Optional list of Points to draw as a route.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = [[" "] * CANVAS_SIZE for _ in range(CANVAS_SIZE)]

        for row in range(CANVAS_SIZE):
            for col in range(CANVAS_SIZE):
                if row % 2 == 1 and col % 2 == 1:
                    canvas[row][col] = self.map_symbol_empty

        for value in range(0, MAP_SIZE + 1, CELL_SIZE):
            index = self._index(value)
            for other in range(CANVAS_SIZE):
                canvas[index][other] = self.map_symbol_street
                canvas[other][index] = self.map_symbol_street

        if route_waypoints:
            self._draw_route(canvas, route_waypoints)

        for order in orders:
            if order.status == "completed":
                continue
            canvas[self._index(order.restaurant_y)][
                self._index(order.restaurant_x)] = self.map_symbol_restaurant
            canvas[self._index(order.customer_y)][
                self._index(order.customer_x)] = self.map_symbol_customer

        for rider in riders:
            canvas[self._index(rider.y)][
                self._index(rider.x)] = self.map_symbol_rider

        lines = ["".join(row) for row in canvas]
        legend = ("Legend: R rider  S restaurant  C customer  "
                  "# street  . cell center  * route")
        return "\n".join(lines) + "\n" + legend

    def _draw_route(self, canvas, waypoints):
        """Draw axis-aligned route segments onto the canvas."""
        for start, end in zip(waypoints, waypoints[1:]):
            ax, ay = self._index(start.x), self._index(start.y)
            bx, by = self._index(end.x), self._index(end.y)
            if ax == bx:
                for row in range(min(ay, by), max(ay, by) + 1):
                    canvas[row][ax] = self.map_symbol_route
            elif ay == by:
                for col in range(min(ax, bx), max(ax, bx) + 1):
                    canvas[ay][col] = self.map_symbol_route
        if len(waypoints) == 1:
            canvas[self._index(waypoints[0].y)][
                self._index(waypoints[0].x)] = self.map_symbol_route

    def format_status(self, system):
        """Return a snapshot of funds, riders and their orders.

        Args:
            system: The SystemManager instance.
        """
        lines = [
            f"=== System Status (tick {system.current_tick}) ===",
            f"Funds: {system.funds}",
            f"Riders: {len(system.riders)}",
            f"Pending orders: {system.order_manager.pending_count()}",
        ]
        if not system.riders:
            lines.append("No riders on duty.")
        for rider in system.riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id} | position ({rider.x}, {rider.y})"
                f" | state: {STATE_NAMES.get(rider.state, 'unknown')}"
                f" | orders: {len(rider.orders)} {order_ids}")
        return "\n".join(lines)

    def format_orders(self, orders):
        """Return a table of order details.

        Args:
            orders: Iterable of Order objects.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} | {'start':>6} | {'restaurant':>12} | "
                  f"{'customer':>12} | {'distance':>8} | {'taken':>6} | "
                  f"{'rider':>5} | status")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else str(order.rider_id)
            lines.append(
                f"{order.id:>4} | {order.start_time:>6} | "
                f"{str((order.restaurant_x, order.restaurant_y)):>12} | "
                f"{str((order.customer_x, order.customer_y)):>12} | "
                f"{order.distance:>8.1f} | {taken:>6} | {rider:>5} | "
                f"{order.status}")
        return "\n".join(lines)

    def format_rider_log(self, riders):
        """Return every recorded status change for all riders.

        Args:
            riders: Iterable of Rider objects.
        """
        lines = []
        for rider in riders:
            lines.append(f"=== Rider #{rider.rider_id} log ===")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = ("-" if entry["order_id"] is None
                         else f"#{entry['order_id']}")
                lines.append(
                    f"  tick {entry['tick']:>4} | {entry['event']:<22} | "
                    f"order {order:>4} | at ({entry['x']}, {entry['y']})")
        if not lines:
            return "No riders on duty."
        return "\n".join(lines)
