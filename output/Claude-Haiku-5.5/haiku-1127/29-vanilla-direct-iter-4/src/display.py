"""Status text formatting and ASCII map rendering."""

import globalvar
from path_planner import is_street_point
from rider import STATE_NAMES

MAP_SIZE = 800
STEP = 50
STREET_CHAR = "#"
EMPTY_CHAR = "."
RIDER_CHAR = "R"
RESTAURANT_CHAR = "S"
CUSTOMER_CHAR = "C"
ROUTE_CHAR = "*"


class DisplayManager:
    """Produces text snapshots, order tables, rider logs and the ASCII map.

    The 8x8 cell map is drawn on a 17x17 character canvas: cell centres sit at
    odd canvas indices and streets at even indices, so each character is a
    50-unit step of the map.
    """

    def __init__(self, map_size=MAP_SIZE, step=STEP):
        """Create a display manager.

        Args:
            map_size: Side length of the map in units.
            step: Units represented by one canvas character.
        """
        self.map_size = map_size
        self.step = step
        self.size = map_size // step + 1

    def _index(self, value):
        """Convert a coordinate to a canvas index (rounded)."""
        return int(value / self.step + 0.5)

    def _put(self, canvas, point, char):
        """Place a character on the canvas at a map point."""
        col = min(max(self._index(point[0]), 0), self.size - 1)
        row = min(max(self._index(point[1]), 0), self.size - 1)
        canvas[row][col] = char

    def _draw_segment(self, canvas, start, end):
        """Draw a horizontal or vertical route segment with route characters."""
        c1, r1 = self._index(start[0]), self._index(start[1])
        c2, r2 = self._index(end[0]), self._index(end[1])
        if c1 == c2:
            for row in range(min(r1, r2), max(r1, r2) + 1):
                canvas[row][c1] = ROUTE_CHAR
        else:
            for col in range(min(c1, c2), max(c1, c2) + 1):
                canvas[r1][col] = ROUTE_CHAR

    def render_map(self, route=None, origin=None):
        """Render the ASCII map with riders, orders and an optional route.

        Legend: R rider, S restaurant, C customer, . empty cell centre,
        # street, * planned route.

        Args:
            route: Optional list of waypoints to draw as connected segments.
            origin: Optional route start point (drawn as part of the line).

        Returns:
            Multi-line string.
        """
        n = self.size
        canvas = [[EMPTY_CHAR] * n for _ in range(n)]
        for row in range(n):
            for col in range(n):
                if is_street_point(col * self.step, row * self.step):
                    canvas[row][col] = STREET_CHAR

        if route:
            points = ([origin] if origin else []) + list(route)
            for start, end in zip(points, points[1:]):
                self._draw_segment(canvas, start, end)

        for order in globalvar.get_value("orders") or []:
            if order.status == "completed":
                continue
            self._put(canvas, order.res_pos, RESTAURANT_CHAR)
            self._put(canvas, order.cus_pos, CUSTOMER_CHAR)
        for rider in globalvar.get_value("riders") or []:
            self._put(canvas, rider.position, RIDER_CHAR)

        lines = ["Map (x across, y up; labels are coordinates / 100):"]
        header = "     " + " ".join(
            str(col * self.step // 100) if (col * self.step) % 100 == 0 else " "
            for col in range(n))
        lines.append(header)
        for row in reversed(range(n)):
            label = f"{row * self.step:>4} "
            lines.append(label + " ".join(canvas[row]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer .=empty #=street *=route")
        return "\n".join(lines)

    def format_status(self, funds, riders, active_orders):
        """Format the system status snapshot.

        Args:
            funds: Current system funds.
            riders: List of riders.
            active_orders: Number of unfinished orders.

        Returns:
            Multi-line status string.
        """
        lines = [f"System funds: {funds}",
                 f"Riders: {len(riders)}",
                 f"Unfinished orders: {active_orders}"]
        for rider in riders:
            order_ids = ", ".join(f"#{o.id}" for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"status {STATE_NAMES.get(rider.state, 'unknown')}, "
                f"orders {len(rider.orders)} [{order_ids}]")
        return "\n".join(lines)

    def format_orders(self, orders):
        """Format every order with timing, distance and rider details.

        Args:
            orders: List of Order objects.

        Returns:
            Multi-line string (or a notice when there are no orders).
        """
        if not orders:
            return "No orders yet."
        lines = []
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"Order #{o.id}: start tick {o.start_time}, "
                f"restaurant {o.res_pos}, customer {o.cus_pos}, "
                f"distance {o.distance} units, time taken {taken} ticks, "
                f"rider {rider}, status {o.status}")
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """Format the status-change log of every rider.

        Args:
            riders: List of Rider objects.

        Returns:
            Multi-line string (or a notice when there are no riders).
        """
        if not riders:
            return "No riders recruited yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                state = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:>4}  {entry['event']:<22} order {order:<6} "
                    f"at ({entry['x']}, {entry['y']})  state {state}")
        return "\n".join(lines)
