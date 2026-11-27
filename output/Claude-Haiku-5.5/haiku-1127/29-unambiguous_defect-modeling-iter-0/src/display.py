"""Status display and ASCII map rendering."""

from grid import MAP_SIZE, LATTICE_STEP, is_street_point
from rider import STATE_NAMES

MAX_EVENTS_PER_RIDER = 50


class DisplayManager:
    """Formats status, order, event and map views as text.

    Attributes:
        map_width (int): Width of the ASCII map canvas in characters.
        map_height (int): Height of the ASCII map canvas in characters.

    Map legend:
        ``+`` street intersection/segment node, ``-``/``|`` street segments,
        ``.`` cell centre (block), ``R`` restaurant, ``C`` customer,
        digit rider id (last digit), ``*`` planned route.
    """

    def __init__(self):
        """Create a display manager sized for the 8x8 grid."""
        steps = MAP_SIZE // LATTICE_STEP
        self._steps = steps
        self.map_width = 2 * steps + 1
        self.map_height = 2 * steps + 1

    def _index(self, a, b):
        """Map a lattice node or edge to canvas (row, col).

        Args:
            a: First node (x, y).
            b: Second node (x, y); equal to ``a`` for a node.

        Returns:
            tuple: ``(row, col)`` canvas indices with y increasing upwards.
        """
        col = (a[0] + b[0]) // LATTICE_STEP
        row = 2 * self._steps - (a[1] + b[1]) // LATTICE_STEP
        return row, col

    def render_map(self, riders, orders=(), route=None):
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of active Order objects (restaurants/customers).
            route: Optional list of waypoints to highlight.

        Returns:
            str: Multi-line map with border and legend.
        """
        canvas = [[" "] * self.map_width for _ in range(self.map_height)]
        steps = self._steps
        for i in range(steps + 1):
            for j in range(steps + 1):
                x, y = i * LATTICE_STEP, j * LATTICE_STEP
                r, c = self._index((x, y), (x, y))
                canvas[r][c] = "+" if is_street_point(x, y) else "."
                if j < steps and x % 100 == 0:
                    r, c = self._index((x, y), (x, y + LATTICE_STEP))
                    canvas[r][c] = "|"
                if i < steps and y % 100 == 0:
                    r, c = self._index((x, y), (x + LATTICE_STEP, y))
                    canvas[r][c] = "-"
        if route:
            for point in route:
                r, c = self._index(point, point)
                canvas[r][c] = "*"
            for a, b in zip(route, route[1:]):
                r, c = self._index(a, b)
                canvas[r][c] = "*"
        for order in orders:
            r, c = self._index(order.res_pos, order.res_pos)
            canvas[r][c] = "R"
            r, c = self._index(order.cus_pos, order.cus_pos)
            canvas[r][c] = "C"
        for rider in riders:
            r, c = self._index((rider.x, rider.y), (rider.x, rider.y))
            canvas[r][c] = str(rider.rider_id % 10)
        border = "+" + "-" * self.map_width + "+"
        rows = ["|" + "".join(row) + "|" for row in canvas]
        legend = ("Legend: + street node, -/| street, . block centre, R restaurant, "
                  "C customer, digit rider id, * route")
        return "\n".join([border] + rows + [border, legend])

    def render_status(self, system):
        """Render the status snapshot: funds, riders, orders and consistency.

        Args:
            system: SystemManager instance.

        Returns:
            str: Formatted status text.
        """
        riders = system.riders
        lines = [
            f"System funds : {system.funds}",
            f"Current tick : {system.current_tick}",
            f"Riders       : {len(riders)} (max {system.max_riders})",
            f"Active orders: {len(system.order_manager.active_orders())}",
        ]
        for rider in riders:
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"state={STATE_NAMES.get(rider.state, 'unknown')} speed={rider.speed} "
                f"orders={len(rider.orders)} special_case={'yes' if rider.special_case else 'no'}"
            )
            for order in rider.orders:
                lines.append(f"      order #{order.id} [{order.status}] "
                             f"restaurant={order.res_pos} customer={order.cus_pos}")
        issues = system.check_consistency()
        if issues:
            lines.append("Consistency: repaired issues:")
            lines.extend(f"  - {issue}" for issue in issues)
        else:
            lines.append("Consistency: OK")
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Formatted table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = ["ID   start  restaurant    customer      distance  taken  rider  status"]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            lines.append(
                f"{o.id:<4} {o.start_time:<6} {str(o.res_pos):<13} {str(o.cus_pos):<13} "
                f"{o.distance:<9} {taken:<6} {rider:<6} {o.status}"
            )
        return "\n".join(lines)

    def render_rider_events(self, riders):
        """Render the status-change log of every rider.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: Formatted event text (last MAX_EVENTS_PER_RIDER per rider).
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({len(rider.log)} events):")
            entries = rider.log[-MAX_EVENTS_PER_RIDER:]
            if len(rider.log) > len(entries):
                lines.append(f"  ... {len(rider.log) - len(entries)} older events omitted")
            for entry in entries:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  tick {entry['tick']:<5} {entry['event']:<22} order {order:<5} "
                    f"state={STATE_NAMES.get(entry['state'], '?'):<11} "
                    f"at ({entry['x']}, {entry['y']}) {entry['description']}"
                )
        return "\n".join(lines)
