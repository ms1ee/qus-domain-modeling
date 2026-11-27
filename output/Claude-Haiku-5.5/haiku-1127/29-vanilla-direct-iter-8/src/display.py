"""Status display and ASCII map visualisation.

The ASCII map uses one character per 50 units, so an 800x800 map is drawn as
a 17x17 character grid. Streets (x or y multiples of 100) appear as '#';
cell centres (restaurant/customer locations) lie between streets.
"""

from config import SETTINGS
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"
SYMBOL_ROUTE = "*"


class DisplayManager:
    """Formats status tables, logs and the ASCII map.

    Class attributes:
        UNIT (int): Map units represented by one character.
    """

    UNIT = 50

    def _index(self, value):
        """Convert a map coordinate to a character index.

        Args:
            value: Coordinate in map units.

        Returns:
            int: Index clamped to the character grid.
        """
        return max(0, min(value // self.UNIT, SETTINGS["map_size"] // self.UNIT))

    @staticmethod
    def _sample_polyline(points):
        """Sample points along axis-aligned polyline segments.

        Args:
            points: Ordered list of ``(x, y)`` vertices.

        Returns:
            list[tuple]: Sampled ``(x, y)`` positions along the polyline.
        """
        samples = []
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps == 0:
                samples.append((x1, y1))
                continue
            for i in range(0, steps + 1, 10):
                samples.append((x1 + (x2 - x1) * i // steps,
                                y1 + (y2 - y1) * i // steps))
            samples.append((x2, y2))
        return samples

    def render_map(self, riders=(), orders=(), route=None):
        """Render the ASCII map of riders, orders and an optional route.

        Symbols: R rider, S restaurant, C customer, # street, . empty,
        * route line. Completed orders are not shown.

        Args:
            riders: Riders to draw.
            orders: Orders whose restaurant and customer should be drawn.
            route: Optional polyline ``[(x, y), ...]`` drawn with '*'.

        Returns:
            str: The multi-line map text.
        """
        size = SETTINGS["map_size"] // self.UNIT + 1
        grid = [[SYMBOL_EMPTY] * size for _ in range(size)]
        for row in range(size):
            for col in range(size):
                if row % 2 == 0 or col % 2 == 0:
                    grid[row][col] = SYMBOL_STREET

        if route:
            for x, y in self._sample_polyline(route):
                grid[self._index(y)][self._index(x)] = SYMBOL_ROUTE

        for order in orders:
            if order.status == "completed":
                continue
            rx, ry = order.res_pos
            cx, cy = order.cus_pos
            grid[self._index(ry)][self._index(rx)] = SYMBOL_RESTAURANT
            grid[self._index(cy)][self._index(cx)] = SYMBOL_CUSTOMER

        for rider in riders:
            grid[self._index(rider.y)][self._index(rider.x)] = SYMBOL_RIDER

        lines = []
        for row in range(size):
            label = f"{row * self.UNIT:>4}" if row % 2 == 0 else "    "
            lines.append(f"{label} " + " ".join(grid[row]))
        lines.append("R=rider S=restaurant C=customer #=street .=empty "
                     "*=route (1 char = 50 units)")
        return "\n".join(lines)

    def format_status(self, system):
        """Build the status snapshot shown by the ``status`` command.

        Args:
            system: The SystemManager.

        Returns:
            str: Funds, rider counts and each rider's details.
        """
        riders = system.riders
        lines = [
            f"System status at tick {system.tick_count}",
            f"  Funds: {system.funds}",
            f"  Riders: {len(riders)} (idle: {system.idle_count()})",
            f"  Pending orders: {system.pending_count()}",
        ]
        if not riders:
            lines.append("  No riders on duty.")
        for rider in riders:
            order_text = ", ".join(
                f"#{o.id} ({o.status})" for o in rider.orders) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"status {rider.state_name}, orders {len(rider.orders)} "
                f"[{order_text}]"
            )
        return "\n".join(lines)

    def format_orders(self, orders):
        """Build the table shown by the ``orders`` command.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Table text with start tick, locations, distance, time taken,
            assigned rider and status.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} "
                  f"{'Customer':>12} {'Dist':>6} {'Taken':>6} "
                  f"{'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = order.time_taken()
            taken_text = "-" if taken is None else str(taken)
            rider_text = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>6} {taken_text:>6} {rider_text:>6} "
                f"{order.status:>10}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """Build the status-change log shown by the ``riders`` command.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: One block per rider with every recorded status change.
        """
        riders = list(riders)
        if not riders:
            return "No riders."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}) "
                         f"- {len(rider.log)} record(s)")
            for entry in rider.log:
                order_text = ("-" if entry["order_id"] is None
                              else f"#{entry['order_id']}")
                state_text = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | "
                    f"order {order_text:>5} | position ({entry['x']}, "
                    f"{entry['y']}) | state {state_text}"
                )
        return "\n".join(lines)
