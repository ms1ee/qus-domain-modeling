"""Display helpers: status text, tables and ASCII map rendering."""

import config
import grid

ROUTE_STEP = 50  # Canvas resolution: one character per 50 units.


class DisplayManager:
    """Formats status information and renders ASCII maps.

    Symbols: 'R' rider, 'S' restaurant, 'C' customer, '.' empty,
    '#' street segment, '+' intersection, '*' route.
    """

    # ------------------------------------------------------------------
    # Maps
    # ------------------------------------------------------------------
    def render_cell_map(self, riders, orders):
        """Render the 8x8 cell map showing riders and active order locations.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects; completed ones are skipped.

        Returns:
            str: Multi-line map text.
        """
        size = config.GRID_SIZE
        cells = [["." for _ in range(size)] for _ in range(size)]
        for order in orders:
            if order.status == "completed":
                continue
            cx, cy = order.cus_grid
            cells[grid.cell_index(cy)][grid.cell_index(cx)] = "C"
            rx, ry = order.res_grid
            cells[grid.cell_index(ry)][grid.cell_index(rx)] = "S"
        for rider in riders:
            cells[grid.cell_index(rider.y)][grid.cell_index(rider.x)] = "R"

        lines = ["Cell map (8x8, each cell 100x100 units; top row = highest y)"]
        lines.append("      " + " ".join(str(c) for c in range(size)) + "   <- x cell")
        for row in reversed(range(size)):
            lines.append(f"y{row} | " + " ".join(cells[row]) + " |")
        lines.append("Legend: R=Rider S=Restaurant C=Customer .=Empty")
        return "\n".join(lines)

    def render_street_map(self, riders, orders=(), route_orders=()):
        """Render the street-level ASCII map with routes.

        The canvas has one character per 50 units. Streets run through cell
        centers, so intersections appear at odd indices and route segments
        are drawn as connected '*' lines.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects whose restaurant/customer
                locations should be shown.
            route_orders: Iterable of Order objects whose travelled routes
                should be drawn.

        Returns:
            str: Multi-line map text.
        """
        size = config.MAP_SIZE // ROUTE_STEP + 1
        canvas = [[self._base_char(r, c) for c in range(size)]
                  for r in range(size)]

        for order in route_orders:
            points = order.route
            for start, end in zip(points, points[1:]):
                for px, py in self._segment_points(start, end):
                    row, col = py // ROUTE_STEP, px // ROUTE_STEP
                    if canvas[row][col] not in "RSC":
                        canvas[row][col] = "*"

        for order in orders:
            if order.status == "completed":
                continue
            self._place(canvas, order.cus_grid, "C")
            self._place(canvas, order.res_grid, "S")
        for rider in riders:
            self._place(canvas, rider.position, "R")

        lines = ["Street map (ASCII, 50 units per character; top = highest y)"]
        for row in reversed(range(size)):
            label = f"{row * ROUTE_STEP:>4} "
            lines.append(label + " ".join(canvas[row]))
        lines.append("     " + " ".join(str((c * ROUTE_STEP) // 100 % 10)
                                       if (c * ROUTE_STEP) % 100 == 0 else " "
                                       for c in range(size)) + "  <- x")
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "*=route #=street +=intersection .=block")
        return "\n".join(lines)

    def render_route(self, order, rider=None, riders=()):
        """Render the route of one order as a connected line graph.

        Args:
            order: The Order whose route is drawn.
            rider: Optional rider to mark with 'R' at its current position.
            riders: Optional additional riders to show.

        Returns:
            str: Multi-line map text.
        """
        shown = [rider] if rider is not None else []
        shown.extend(riders)
        return self.render_street_map(shown, [order], [order])

    @staticmethod
    def _base_char(row, col):
        """Return the background character for a canvas position."""
        row_street = row % 2 == 1
        col_street = col % 2 == 1
        if row_street and col_street:
            return "+"
        if row_street or col_street:
            return "#"
        return "."

    @staticmethod
    def _place(canvas, point, symbol):
        """Place a symbol on the canvas at a map coordinate."""
        x, y = point
        canvas[y // ROUTE_STEP][x // ROUTE_STEP] = symbol

    @staticmethod
    def _segment_points(start, end):
        """Return canvas-resolution points along an axis-aligned segment."""
        (ax, ay), (bx, by) = start, end
        points = []
        if ax == bx:
            step = ROUTE_STEP if by >= ay else -ROUTE_STEP
            for y in range(ay, by + step, step):
                points.append((ax, y))
        elif ay == by:
            step = ROUTE_STEP if bx >= ax else -ROUTE_STEP
            for x in range(ax, bx + step, step):
                points.append((x, ay))
        else:
            points = [start, end]
        return points

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    def format_status(self, funds, riders):
        """Format the system snapshot shown by the 'status' command.

        Args:
            funds: Current system funds.
            riders: Iterable of Rider objects.

        Returns:
            str: Multi-line status text.
        """
        riders = list(riders)
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: {rider.state_name():<11} "
                f"pos=({rider.x},{rider.y}) speed={rider.speed} "
                f"orders={order_ids if order_ids else '[]'}")
        return "\n".join(lines)

    def format_orders(self, orders):
        """Format the order table shown by the 'orders' command.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Multi-line table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = []
        for order in orders:
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            taken = order.time_taken if order.time_taken is not None else "-"
            efficiency = (order.efficiency
                          if order.efficiency is not None else "-")
            lines.append(
                f"Order #{order.id}: start_tick={order.start_time} "
                f"restaurant={order.res_pos} customer={order.cus_pos} "
                f"distance={order.distance} time_taken={taken} "
                f"efficiency={efficiency} rider={rider} status={order.status}")
        return "\n".join(lines)

    def format_riders_log(self, riders):
        """Format the status-change history of all riders.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: Multi-line log text.
        """
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} log:")
            for entry in rider.log:
                order_id = entry["order_id"] if entry["order_id"] is not None else "-"
                state = config.STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  tick {entry['tick']:>4} | ({entry['x']},{entry['y']}) | "
                    f"{entry['event']:<22} | order {order_id} | state {state}")
        return "\n".join(lines) if lines else "No riders recruited yet."

    def format_start_summary(self, order, rider, rider_added, estimated_ticks):
        """Format the summary printed after the 'start' command.

        Args:
            order: The created Order.
            rider: The assigned Rider, or None if the order is pending.
            rider_added: True if a new rider was recruited for this order.
            estimated_ticks: Estimated ticks to finish, or None.

        Returns:
            str: Multi-line summary text.
        """
        lines = [
            f"Order #{order.id} created.",
            f"  Restaurant: input {order.res_pos} -> grid center {order.res_grid}",
            f"  Customer:   input {order.cus_pos} -> grid center {order.cus_grid}",
            f"  Distance:   {order.distance} units",
        ]
        lines.append(f"  New rider added: {'yes' if rider_added else 'no'}")
        if rider is not None:
            lines.append(f"  Assigned rider: #{rider.rider_id} "
                         f"(speed {rider.speed} units/tick)")
            if estimated_ticks is not None:
                lines.append(f"  Estimated time: about {estimated_ticks} tick(s)")
        else:
            lines.append("  No rider available; order is pending until a rider "
                         "is recruited.")
        return "\n".join(lines)
