"""Text rendering for the dispatch simulator.

The ASCII map uses a 15x15 canvas: even canvas positions are grid
intersections (cell centers) and odd positions are the streets between them.
"""

import grid
from order_model import COMPLETED
from rider import STATE_NAMES


class DisplayManager:
    """Render status tables, order tables, rider logs and the ASCII map."""

    CANVAS_SIZE = grid.GRID_DIM * 2 - 1
    LEGEND = ("Legend: R=Rider  S=Restaurant  C=Customer  "
              ".=intersection  #=street  *=planned route")

    def _canvas_pos(self, point):
        """Return the ``(row, col)`` canvas position of a map point.

        Row 0 is the top of the map, which corresponds to grid row 7.
        """
        gx, gy = grid.cell_of(point[0], point[1])
        return 2 * (grid.GRID_DIM - 1 - gy), 2 * gx

    def _put(self, canvas, point, symbol):
        """Place a marker symbol on the canvas at a map point."""
        row, col = self._canvas_pos(point)
        canvas[row][col] = symbol

    def _draw_route(self, canvas, start, end):
        """Draw an axis-aligned route segment with ``*`` characters."""
        r1, c1 = self._canvas_pos(start)
        r2, c2 = self._canvas_pos(end)
        for row in range(min(r1, r2), max(r1, r2) + 1):
            for col in range(min(c1, c2), max(c1, c2) + 1):
                canvas[row][col] = "*"

    def render_map(self, riders, orders=None, route=None, start=None):
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Iterable of riders to mark with ``R``.
            orders: Iterable of orders; non-completed orders show ``S``
                (restaurant) and ``C`` (customer).
            route: Optional list of waypoints drawn as a connected line.
            start: Optional starting point of the route.

        Returns:
            str: Multi-line map text.
        """
        size = self.CANVAS_SIZE
        canvas = []
        for row in range(size):
            line = []
            for col in range(size):
                if row % 2 == 0 and col % 2 == 0:
                    line.append(".")
                elif row % 2 == 0 or col % 2 == 0:
                    line.append("#")
                else:
                    line.append(" ")
            canvas.append(line)

        if route:
            points = ([start] if start is not None else []) + list(route)
            for first, second in zip(points, points[1:]):
                self._draw_route(canvas, first, second)
            if len(points) == 1:
                self._draw_route(canvas, points[0], points[0])

        for order in orders or []:
            if order.status == COMPLETED:
                continue
            self._put(canvas, order.cus_grid, "C")
            self._put(canvas, order.res_grid, "S")
        for rider in riders or []:
            self._put(canvas, rider.position, "R")

        lines = ["  " + "".join(
            f"{col // 2 if col % 2 == 0 else ' '} " for col in range(size))]
        for row_index, row in enumerate(canvas):
            label = (str(grid.GRID_DIM - 1 - row_index // 2)
                     if row_index % 2 == 0 else " ")
            lines.append(f"{label} " + "".join(f"{ch} " for ch in row))
        lines.append("(columns = grid x index, rows = grid y index)")
        lines.append(self.LEGEND)
        return "\n".join(lines)

    def render_status(self, funds, riders, pending_count, tick):
        """Render a snapshot of the system state.

        Args:
            funds: Current fund balance.
            riders: List of riders.
            pending_count: Number of orders waiting for a rider.
            tick: Current simulation tick.

        Returns:
            str: Status text.
        """
        lines = [
            f"Simulation tick: {tick}",
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
            f"Pending orders (no rider yet): {pending_count}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            flag = " [special case]" if rider.special_case else ""
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"state {rider.state_name}, speed {rider.speed}, "
                f"orders {order_ids}{flag}")
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
        lines = [
            f"{'ID':<5}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
            f"{'Distance':<10}{'Taken':<7}{'Rider':<7}{'Status':<12}"
            f"{'Eff.':<8}"
        ]
        for order in orders:
            taken = order.time_taken
            taken_text = "-" if taken is None else str(taken)
            rider_text = "-" if order.rider_id is None else f"#{order.rider_id}"
            eff = order.efficiency
            eff_text = "-" if eff is None else f"{eff:.2f}"
            lines.append(
                f"{order.id:<5}{order.start_tick:<7}"
                f"{str(order.restaurant_pos):<13}"
                f"{str(order.customer_pos):<13}"
                f"{order.distance:<10}{taken_text:<7}{rider_text:<7}"
                f"{order.status:<12}{eff_text:<8}")
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render the recorded status changes of every rider.

        Args:
            riders: Iterable of riders.

        Returns:
            str: Log text grouped by rider.
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} ({rider.state_name}):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = ("-" if entry["order_id"] is None
                              else f"order #{entry['order_id']}")
                state_name = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:<6} {entry['event']:<22}"
                    f"{order_text:<12} at ({entry['x']}, {entry['y']}) "
                    f"[{state_name}]")
        return "\n".join(lines)

    def render_assignment(self, rider, order, route, distance, ticks):
        """Render the summary shown after an order is assigned.

        Args:
            rider: The assigned rider.
            order: The new order.
            route: Waypoints of the planned route after the rider position.
            distance: Total route length in units.
            ticks: Estimated number of ticks to complete the route.

        Returns:
            str: Summary text followed by the route map.
        """
        queued = len(rider.orders) - 1
        queue_text = (f" (queued behind {queued} order(s))"
                      if queued > 0 else "")
        lines = [
            f"Order #{order.id} assigned to rider #{rider.rider_id}"
            f"{queue_text}.",
            f"  Rider speed: {rider.speed} units/tick, "
            f"state: {rider.state_name}",
            f"  Restaurant grid point: {order.res_grid}",
            f"  Customer grid point: {order.cus_grid}",
            f"  Route distance: {distance} units, "
            f"estimated time: {ticks} tick(s)",
            "Route map:",
            self.render_map([rider], [order], route, rider.position),
        ]
        return "\n".join(lines)
