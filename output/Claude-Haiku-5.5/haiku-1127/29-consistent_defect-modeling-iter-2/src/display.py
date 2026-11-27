"""Display helpers: status tables, order/rider listings and ASCII maps."""

from grid_map import GridMap

from rider import STATE_NAMES


class DisplayManager:
    """Builds text output for the command-line interface."""

    def __init__(self, grid=None, map_display_size=17):
        """Create a display manager.

        Args:
            grid: Optional :class:`GridMap` used for coordinate scaling.
            map_display_size: Side length of the ASCII canvas in characters.

        Raises:
            ValueError: If the canvas is too small.
        """
        if map_display_size < 2:
            raise ValueError("map_display_size must be at least 2")
        self.grid = grid if grid is not None else GridMap()
        self.map_display_size = map_display_size

    def _scale(self):
        """Return the number of map units per canvas character step."""
        return self.grid.map_size / (self.map_display_size - 1)

    def _to_canvas(self, x, y):
        """Convert map coordinates to canvas ``(row, col)`` indices."""
        scale = self._scale()
        n = self.map_display_size
        col = min(max(int(round(x / scale)), 0), n - 1)
        row = min(max(int(round(y / scale)), 0), n - 1)
        return row, col

    def render_status(self, system, issues=None):
        """Return a snapshot of funds, riders and their orders.

        Args:
            system: The :class:`SystemManager`.
            issues: Optional list of consistency issue strings.
        """
        lines = [
            f"=== System Status (tick {system.tick}) ===",
            f"System funds : {system.funds}",
            f"Rider count  : {len(system.riders)}",
        ]
        for rider in system.riders:
            active = [o.order_id for o in rider.active_orders()]
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"state {STATE_NAMES.get(rider.state, rider.state)}, "
                f"active orders {len(active)} {active}"
            )
        if issues is None:
            lines.append("Consistency: not checked")
        elif issues:
            lines.append("Consistency issues: " + "; ".join(issues))
        else:
            lines.append("Consistency: OK")
        return "\n".join(lines)

    def render_orders(self, orders):
        """Return a table of all orders.

        Columns: id, start tick, restaurant, customer, distance, time taken,
        status and assigned rider.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>6} {'Taken':>6} {'Status':>11} {'Rider':>6}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>6.0f} {taken:>6} "
                f"{order.status:>11} {rider:>6}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders):
        """Return the event history of every rider."""
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None \
                    else f"order {entry['order_id']}"
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<20} | "
                    f"{order:<10} | at ({entry['x']}, {entry['y']})"
                )
        return "\n".join(lines)

    def render_map(self, riders, orders, route=None):
        """Return an ASCII map of streets, riders, restaurants and customers.

        Symbols: ``R`` rider, ``S`` restaurant, ``C`` customer, ``#`` street,
        ``*`` planned route, ``.`` empty space.

        Args:
            riders: Riders to plot.
            orders: Orders whose restaurant/customer points should be plotted.
            route: Optional list of ``(x, y)`` points drawn as a polyline.
        """
        n = self.map_display_size
        scale = self._scale()
        cell = self.grid.cell_size
        canvas = [["." for _ in range(n)] for _ in range(n)]

        for k in range(n):
            if int(round(k * scale)) % cell == 0:
                for j in range(n):
                    canvas[k][j] = "#"
                    canvas[j][k] = "#"

        if route:
            for a, b in zip(route, route[1:]):
                span = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                steps = max(1, span // 10)
                for i in range(steps + 1):
                    px = a[0] + (b[0] - a[0]) * i / steps
                    py = a[1] + (b[1] - a[1]) * i / steps
                    row, col = self._to_canvas(px, py)
                    canvas[row][col] = "*"

        for order in orders:
            row, col = self._to_canvas(*order.res_pos)
            canvas[row][col] = "S"
        for order in orders:
            row, col = self._to_canvas(*order.cus_pos)
            canvas[row][col] = "C"
        for rider in riders:
            row, col = self._to_canvas(rider.x, rider.y)
            canvas[row][col] = "R"

        body = "\n".join("".join(row) for row in canvas)
        legend = "Legend: R=rider S=restaurant C=customer #=street " \
                 "*=route .=empty"
        return f"{body}\n{legend}"

    def render_route(self, rider, order, route, length, speed, ticks):
        """Return a textual and graphical description of an assigned route.

        Args:
            rider: The assigned rider.
            order: The newly assigned order.
            route: Polyline route points.
            length: Total route length in units.
            speed: Rider speed in units per tick.
            ticks: Estimated number of ticks to finish the route.
        """
        lines = [
            f"Assigned rider: #{rider.rider_id} at ({rider.x}, {rider.y})",
            f"Speed: {speed} units/tick | Route length: {length} units | "
            f"Estimated time: {ticks} ticks",
            "Route map:",
            self.render_map([rider], [order], route),
        ]
        return "\n".join(lines)
