"""Status display and ASCII map rendering."""

from constants import ORDER_COMPLETED, STATE_NAMES

CANVAS_STEP = 50                 # One canvas cell = 50 units; cell centres are odd indices.
CANVAS_SIZE = 17                 # 0..800 in steps of 50, plus one.


class DisplayManager:
    """Formats the system status, order and rider tables, and ASCII maps."""

    # Helpers --------------------------------------------------------------
    @staticmethod
    def _to_index(value):
        """Map a coordinate to a canvas index (nearest 50-unit step)."""
        index = (value + CANVAS_STEP // 2) // CANVAS_STEP
        return min(max(index, 0), CANVAS_SIZE - 1)

    @staticmethod
    def _base_canvas():
        """Create the street canvas: even rows/columns are streets ('#')."""
        return [
            ["#" if (row % 2 == 0 or col % 2 == 0) else "." for col in range(CANVAS_SIZE)]
            for row in range(CANVAS_SIZE)
        ]

    def _place(self, canvas, x, y, symbol):
        """Place ``symbol`` at the canvas cell that corresponds to (x, y)."""
        canvas[self._to_index(y)][self._to_index(x)] = symbol

    @staticmethod
    def _canvas_text(canvas):
        """Render a canvas with coordinate labels on each row and column."""
        header = "      " + " ".join(f"{c * CANVAS_STEP % 1000:>3}" if False else " " for c in range(CANVAS_SIZE))
        lines = []
        for row_index, row in enumerate(canvas):
            label = f"{row_index * CANVAS_STEP:>4} "
            lines.append(label + " ".join(row))
        axis = "     " + " ".join(
            f"{(c * CANVAS_STEP) // 100}" if c % 2 == 0 else " "
            for c in range(CANVAS_SIZE)
        )
        return "\n".join(lines + ["x: 0..800 (100-unit ticks shown by '#' columns)", axis]) \
            if header is not None else ""

    # Textual reports ------------------------------------------------------
    @staticmethod
    def format_funds(funds):
        """Return a one-line fund balance string."""
        return f"System funds: {funds}"

    def render_status(self, funds, riders, tick, pending_count):
        """Render the snapshot shown by the ``status`` command.

        Args:
            funds: Current fund balance.
            riders: Iterable of Rider objects.
            tick: Current simulated tick.
            pending_count: Number of unassigned orders.

        Returns:
            str: Multi-line report.
        """
        riders = list(riders)
        lines = [
            f"Tick: {tick}",
            self.format_funds(funds),
            f"Riders: {len(riders)}  Pending orders: {pending_count}",
        ]
        if not riders:
            lines.append("No riders on duty.")
        for rider in riders:
            order_ids = [o.id for o in rider.orders] or "none"
            lines.append(
                f"  R{rider.rider_id}: pos=({rider.x},{rider.y}) "
                f"status={STATE_NAMES.get(rider.state, rider.state)} "
                f"orders={len(rider.orders)} {order_ids}"
            )
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
            f"{'ID':>4} {'Start':>6} {'Restaurant':>14} {'Customer':>14} "
            f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>12}"
        ]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"R{o.rider_id}"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str(o.res_pos):>14} {str(o.cus_pos):>14} "
                f"{o.distance:>6} {taken:>6} {rider:>6} {o.status:>12}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render every recorded status change for all riders.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: One line per event, ordered by rider then time.
        """
        lines = []
        for rider in riders:
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"[t={entry['time']:>4}] R{entry['rider_id']} "
                    f"{entry['event']:<22} order={order_text:<5} "
                    f"pos=({entry['x']},{entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], entry['state'])}"
                )
        return "\n".join(lines) if lines else "No rider events recorded."

    # Maps -----------------------------------------------------------------
    def render_map(self, riders, orders):
        """Render the ASCII map of riders and active orders.

        Symbols: R rider, S restaurant, C customer, '.' empty cell centre,
        '#' street.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects (completed orders are hidden).

        Returns:
            str: Map text with a legend.
        """
        canvas = self._base_canvas()
        for order in orders:
            if order.status == ORDER_COMPLETED:
                continue
            self._place(canvas, *order.res_pos, "S")
            self._place(canvas, *order.cus_pos, "C")
        for rider in riders:
            self._place(canvas, rider.x, rider.y, "R")
        return self._format_canvas(canvas) + (
            "\nLegend: R=Rider S=Restaurant C=Customer .=empty #=street"
        )

    def render_route(self, order, points, speed, ticks):
        """Render the projected route of the assigned rider as a line graph.

        Args:
            order: The Order being routed.
            points: List of (x, y) positions from the start to the customer.
            speed: Rider speed in units per tick.
            ticks: Projected number of ticks.

        Returns:
            str: Route header and ASCII map with '*' marking the path.
        """
        canvas = self._base_canvas()
        length = 0
        for (px, py), (qx, qy) in zip(points, points[1:]):
            length += abs(qx - px) + abs(qy - py)
        for x, y in points:
            self._place(canvas, x, y, "*")
        self._place(canvas, *order.res_pos, "S")
        self._place(canvas, *order.cus_pos, "C")
        if points:
            self._place(canvas, *points[0], "R")
        header = [
            f"Route for order {order.id}: restaurant {order.input_res} -> "
            f"grid centre {order.res_pos}",
            f"  customer {order.input_cus} -> grid centre {order.cus_pos}",
            f"  Speed: {speed} units/tick | Projected time: {ticks} ticks | "
            f"Route length: {length} units",
        ]
        return "\n".join(header) + "\n" + self._format_canvas(canvas) + (
            "\nLegend: R=Rider S=Restaurant C=Customer *=route #=street .=empty"
        )

    @staticmethod
    def _format_canvas(canvas):
        """Format a canvas with y-axis labels and an x-axis ruler."""
        lines = []
        for row_index, row in enumerate(canvas):
            label = f"{row_index * CANVAS_STEP:>4} "
            lines.append(label + " ".join(row))
        ruler = "     " + " ".join(
            (str((col * CANVAS_STEP) // 100) if col % 2 == 0 else " ")
            for col in range(CANVAS_SIZE)
        )
        lines.append(ruler)
        lines.append("     (x axis: hundreds of units; y axis labelled in units)")
        return "\n".join(lines)
