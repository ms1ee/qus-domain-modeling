"""Status display and ASCII map visualisation."""

import math

import globalvar
from config import CONFIG
from path_planner import PathPlanner
from rider import STATE_NAMES


class DisplayManager:
    """Renders status reports, order tables, rider histories and the map.

    The map uses one character per 50 units in both directions, so streets
    (multiples of the 100-unit cell size) fall on even character indices and
    cell centres fall on odd ones. An 800x800 map is therefore a 17x17 canvas.

    Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty cell,
    '#' street, '*' route.

    Attributes:
        system: The SystemManager being displayed.
        map_width, map_height: Canvas dimensions in characters.
    """

    EMPTY = "."
    STREET = "#"
    ROUTE = "*"
    RIDER = "R"
    RESTAURANT = "S"
    CUSTOMER = "C"
    LEGEND = "Legend: R=Rider S=Restaurant C=Customer .=empty #=street *=route"

    def __init__(self, system):
        """Create a display bound to a system.

        Args:
            system: SystemManager instance.
        """
        self.system = system
        self.scale = max(1, CONFIG["cell_size"] // 2)
        self.map_width = CONFIG["map_size"] // self.scale + 1
        self.map_height = self.map_width

    def _index(self, value):
        """Convert a map coordinate to a canvas index."""
        index = int(round(value / self.scale))
        return min(max(index, 0), self.map_width - 1)

    def _blank_canvas(self):
        """Create a canvas containing only streets and empty cells."""
        cell = CONFIG["cell_size"]
        canvas = []
        for row in range(self.map_height):
            y = row * self.scale
            line = []
            for col in range(self.map_width):
                x = col * self.scale
                on_street = y % cell == 0 or x % cell == 0
                line.append(self.STREET if on_street else self.EMPTY)
            canvas.append(line)
        return canvas

    def _plot(self, canvas, point, symbol):
        """Place a symbol at a map coordinate."""
        x, y = point
        canvas[self._index(y)][self._index(x)] = symbol

    def _draw_polyline(self, canvas, points):
        """Draw connected axis-aligned segments with the route symbol."""
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            c1, r1 = self._index(x1), self._index(y1)
            c2, r2 = self._index(x2), self._index(y2)
            if r1 == r2:
                for col in range(min(c1, c2), max(c1, c2) + 1):
                    canvas[r1][col] = self.ROUTE
            elif c1 == c2:
                for row in range(min(r1, r2), max(r1, r2) + 1):
                    canvas[row][c1] = self.ROUTE
            else:
                # Fallback for non-aligned points: horizontal then vertical.
                for col in range(min(c1, c2), max(c1, c2) + 1):
                    canvas[r1][col] = self.ROUTE
                for row in range(min(r1, r2), max(r1, r2) + 1):
                    canvas[row][c2] = self.ROUTE

    def render_map(self, riders=None, orders=None, routes=None):
        """Render the ASCII map.

        Args:
            riders: Riders to plot (defaults to all system riders).
            orders: Orders whose restaurant/customer should be plotted
                (defaults to all active orders).
            routes: Optional list of point lists drawn as route polylines.

        Returns:
            Multi-line string containing the map and a legend.
        """
        if riders is None:
            riders = self.system.riders
        if orders is None:
            orders = globalvar.get_value("orders") or []

        canvas = self._blank_canvas()
        for points in routes or []:
            self._draw_polyline(canvas, points)
        for order in orders:
            if order.status == "completed":
                continue
            self._plot(canvas, order.restaurant_center, self.RESTAURANT)
            self._plot(canvas, order.customer_center, self.CUSTOMER)
        for rider in riders:
            self._plot(canvas, (rider.x, rider.y), self.RIDER)

        lines = []
        for row in range(self.map_height - 1, -1, -1):
            label = f"{row * self.scale:>4} "
            lines.append(label + " ".join(canvas[row]))
        lines.append("     x: 0 (left) .. 800 (right); y: 0 (bottom) .. 800 (top)")
        lines.append(self.LEGEND)
        return "\n".join(lines)

    def render_route(self, rider, order):
        """Describe and draw the route a rider will follow for an order.

        Args:
            rider: The assigned Rider.
            order: The Order being served.

        Returns:
            Text containing the route map, speed and time estimate.
        """
        planner = PathPlanner()
        speed = max(1, rider.speed)
        start = (rider.x, rider.y)
        leg1 = planner.plan(start, order.restaurant_center, speed)
        leg2 = planner.plan(order.restaurant_center, order.customer_center, speed)
        points = [start] + leg1.waypoints + leg2.waypoints
        total = leg1.total_distance + leg2.total_distance
        ticks = math.ceil(total / speed)
        header = [
            f"Route for rider #{rider.rider_id}: speed {speed} units/tick",
            f"Restaurant grid centre: {order.restaurant_center}, "
            f"Customer grid centre: {order.customer_center}",
            f"Route distance: {total} units, estimated time: {ticks} tick(s)",
        ]
        return "\n".join(header + [self.render_map([rider], [order], [points])])

    def render_status(self):
        """Render the system status snapshot.

        Returns:
            Multi-line status text including funds, riders and consistency.
        """
        riders = self.system.riders
        orders = globalvar.get_value("orders") or []
        active = [order for order in orders if order.status != "completed"]
        lines = [
            f"Tick: {self.system.tick}",
            f"System funds: {self.system.funds}",
            f"Riders: {len(riders)}",
            f"Active orders: {len(active)}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders] or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x},{rider.y}), "
                f"state {STATE_NAMES.get(rider.state, 'unknown')}, "
                f"orders {order_ids}, special case {rider.special_case}"
            )
        problems = self.system.check_consistency()
        if problems:
            lines.append("Consistency issues:")
            lines.extend(f"  - {problem}" for problem in problems)
        else:
            lines.append("Consistency: OK")
        return "\n".join(lines)

    def render_orders(self):
        """Render a table of all orders.

        Returns:
            Multi-line table text.
        """
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders yet."
        lines = [
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Distance':>9} {'Taken':>6} {'Rider':>6} {'Status':<12}"
        ]
        for order in orders:
            restaurant = f"({order.restaurant_x},{order.restaurant_y})"
            customer = f"({order.customer_x},{order.customer_y})"
            start = "-" if order.start_time is None else str(order.start_time)
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {start:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>9} {taken:>6} {rider:>6} {order.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_history(self):
        """Render every recorded status change for all riders.

        Returns:
            Multi-line text with time, event, order number, position and state.
        """
        riders = self.system.riders
        if not riders:
            return "No riders."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (distance travelled: {rider.distance_travelled})")
            if not rider.history:
                lines.append("  (no status changes)")
            for entry in rider.history:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:>4} {entry['event']:<22} order {order:<5} "
                    f"pos ({entry['x']},{entry['y']}) state "
                    f"{STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines)
