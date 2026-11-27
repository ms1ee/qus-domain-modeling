"""Status display and ASCII map visualization."""

import config
import grid
from rider import STATE_NAMES

HALF = config.CELL_SIZE // 2  # 50 units per canvas character
CANVAS_SIZE = 2 * config.GRID_CELLS + 1  # 17 characters per side
MAP_LEGEND = (
    "Legend: + intersection, -/| street, R restaurant, C customer, "
    "0-9 rider (id mod 10), * route"
)


def _cell_label(center):
    """Return a short ``[col, row]`` label for a cell center."""
    return f"[{grid.cell_index(center[0])}, {grid.cell_index(center[1])}]"


def _move_toward(value, target, step):
    """Move ``value`` toward ``target`` by at most ``step``."""
    if value == target:
        return value
    delta = target - value
    move = min(step, abs(delta))
    return value + move if delta > 0 else value - move


class DisplayManager:
    """Renders the system status, order tables and the ASCII map.

    The canvas uses 50-unit characters: even indices are street lines
    (multiples of 100) and odd indices are cell centers.
    """

    def render_map(self, riders=(), orders=(), trail=None):
        """Render the 8x8 ASCII map.

        Args:
            riders: Riders to draw (digit = rider_id % 10).
            orders: Orders whose restaurant (R) and customer (C) to draw.
            trail: Optional list of ``(x, y)`` points drawn as a route.

        Returns:
            str: Multi-line map text.
        """
        canvas = self._base_canvas()
        if trail:
            self._draw_trail(canvas, trail)
        for order in orders:
            self._put(canvas, order.res_pos[0], order.res_pos[1], "R")
            self._put(canvas, order.cus_pos[0], order.cus_pos[1], "C")
        for rider in riders:
            self._put(canvas, rider.x, rider.y, str(rider.rider_id % 10))
        return self._frame(canvas)

    def render_status(self, funds, riders, tick):
        """Render the system status snapshot.

        Args:
            funds: Current system funds.
            riders: List of riders.
            tick: Current simulated tick.

        Returns:
            str: Status text.
        """
        lines = [
            f"=== System status @ tick {tick} ===",
            f"Funds: {funds}",
            f"Riders: {len(riders)}/{config.MAX_RIDERS}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            lines.append(
                f"  Rider {rider.rider_id:>3}: pos=({rider.x:>3},{rider.y:>3}) "
                f"state={STATE_NAMES.get(rider.state, 'unknown'):<11} "
                f"speed={rider.speed:>2} orders={len(rider.orders)} [{order_ids}]"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of order details.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Table text.
        """
        orders = list(orders)
        header = (
            f"{'ID':>4} {'Status':<10} {'Start':>6} {'Restaurant':<12} "
            f"{'Customer':<12} {'Dist':>5} {'Taken':>6} {'Rider':>6}"
        )
        lines = [f"=== Orders ({len(orders)}) ===", header, "-" * len(header)]
        if not orders:
            lines.append("  (no orders yet)")
        for order in orders:
            start = "-" if order.start_tick is None else str(order.start_tick)
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else str(order.rider_id)
            lines.append(
                f"{order.id:>4} {order.status:<10} {start:>6} "
                f"{str(order.res_pos):<12} {str(order.cus_pos):<12} "
                f"{order.distance:>5} {taken:>6} {rider:>6}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Render the status-change log for every rider.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: Log text grouped by rider.
        """
        riders = list(riders)
        lines = [f"=== Rider event log ({len(riders)} riders) ==="]
        if not riders:
            lines.append("  (no riders yet)")
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} (speed {rider.speed}):")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order_text = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                detail = ""
                if entry["event"] == "state_change":
                    detail = (
                        f" {STATE_NAMES.get(entry.get('from_state'), '?')} -> "
                        f"{STATE_NAMES.get(entry.get('to_state'), '?')}"
                    )
                lines.append(
                    f"  t={entry['time']:>5} {entry['event']:<20} order={order_text:<6} "
                    f"pos=({entry['x']},{entry['y']}){detail}"
                )
        return "\n".join(lines)

    def render_order_placed(self, order, rider, new_rider):
        """Describe a newly placed and assigned order.

        Args:
            order: The order that was created.
            rider: The rider it was assigned to.
            new_rider: True if a rider was recruited for this order.

        Returns:
            str: Summary text.
        """
        rx, ry = order.res_input
        cx, cy = order.cus_input
        lines = [
            f"Order #{order.id} created at tick {order.created_tick}.",
            f"  Restaurant input ({rx},{ry}) -> grid cell {_cell_label(order.res_pos)} "
            f"center {order.res_pos}",
            f"  Customer   input ({cx},{cy}) -> grid cell {_cell_label(order.cus_pos)} "
            f"center {order.cus_pos}",
            f"  Trip distance (restaurant -> customer): {order.distance} units",
            f"  New rider added: {'yes' if new_rider else 'no'}",
            f"  Assigned to Rider #{rider.rider_id} at {rider.position}, "
            f"speed {rider.speed} units/tick",
            f"  Rider distance to restaurant: "
            f"{grid.manhattan(rider.position, order.restaurant_node)} units",
        ]
        return "\n".join(lines)

    def render_route(self, order, rider, trail):
        """Describe and draw the route taken by a rider for an order.

        Args:
            order: The completed (or timed-out) order.
            rider: The rider that served the order.
            trail: Positions of the rider after each tick, starting at assignment.

        Returns:
            str: Route summary followed by the ASCII route map.
        """
        taken = order.time_taken
        taken_text = "not completed" if taken is None else f"{taken} ticks"
        lines = [
            f"Route for Order #{order.id} by Rider #{rider.rider_id} "
            f"(speed {rider.speed} units/tick)",
            f"  Time taken: {taken_text}",
            f"  Steps simulated: {max(0, len(trail) - 1)}",
            f"  Efficiency: "
            f"{'-' if order.efficiency is None else f'{order.efficiency:.2f} units/tick'}",
            "",
            self.render_map(riders=[rider], orders=[order], trail=trail),
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Canvas helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _base_canvas():
        """Create the empty street canvas."""
        canvas = []
        for row in range(CANVAS_SIZE):
            line = []
            for col in range(CANVAS_SIZE):
                if row % 2 == 0 and col % 2 == 0:
                    ch = "+"
                elif row % 2 == 0:
                    ch = "-"
                elif col % 2 == 0:
                    ch = "|"
                else:
                    ch = " "
                line.append(ch)
            canvas.append(line)
        return canvas

    @staticmethod
    def _index(value):
        """Map a coordinate to a canvas index (0-16)."""
        clamped = max(0, min(int(value), config.MAP_SIZE))
        return min(clamped // HALF, CANVAS_SIZE - 1)

    def _put(self, canvas, x, y, symbol):
        """Place ``symbol`` at map coordinate ``(x, y)``."""
        col = self._index(x)
        row = CANVAS_SIZE - 1 - self._index(y)
        canvas[row][col] = symbol

    @staticmethod
    def _segment(a, b):
        """Return intermediate points (10-unit steps) from ``a`` to ``b``."""
        points = []
        x, y = a
        tx, ty = b
        while (x, y) != (tx, ty):
            x = _move_toward(x, tx, 10)
            y = _move_toward(y, ty, 10)
            points.append((x, y))
        return points

    def _draw_trail(self, canvas, trail):
        """Draw the route as a connected line through the trail points."""
        previous = None
        for point in trail:
            if previous is None:
                self._put(canvas, point[0], point[1], "*")
            else:
                for x, y in self._segment(previous, point):
                    self._put(canvas, x, y, "*")
            previous = point

    @staticmethod
    def _frame(canvas):
        """Convert the canvas into labelled multi-line text."""
        lines = []
        for row_index, row in enumerate(canvas):
            y = config.MAP_SIZE - row_index * HALF
            label = f"{y:>4} " if row_index % 2 == 0 else "     "
            lines.append(label + "".join(row))
        lines.append("     x: 0 .. 800 (street intersections every 100 units)")
        lines.append("     " + MAP_LEGEND)
        return "\n".join(lines)
