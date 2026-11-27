"""Status displays and ASCII map visualisation."""

import math

from globalvar import get_value
from path_planner import CELL_SIZE, GRID_DIM, ROAD_OFFSET
from rider import STATE_NAMES

CANVAS = 2 * GRID_DIM - 1
SYM_NODE = "+"
SYM_H_STREET = "-"
SYM_V_STREET = "|"
SYM_EMPTY = " "
SYM_RESTAURANT = "R"
SYM_CUSTOMER = "C"
SYM_RIDER = "@"
SYM_ROUTE = "*"

HELP_TEXT = """Commands (shortcuts in brackets):
  start [rx ry cx cy] (s)  Create an order: restaurant then customer coordinates (0-800)
  status (st)              Show system funds and every rider's state and orders
  orders (o)               Show details for all orders
  riders (r)               Show status-change log for every rider
  tick [n] (t)             Advance the simulation by n ticks (default 1)
  map (m)                  Show the ASCII street map with riders and restaurants
  save [file] (w)          Save state to JSON (default dispatch_state.json)
  history (hist)           Show command history
  help (h)                 Show this help
  quit / exit (q)          Exit the program
Shortcuts: !! repeats the last command, !n repeats history entry n."""


class DisplayManager:
    """Builds textual status reports and the ASCII map."""

    @staticmethod
    def _canvas_index(value):
        """Convert a map coordinate to a canvas row or column index.

        Cell centres (50 + 100k) map to even indices 2k; street midpoints map
        to odd indices.

        Args:
            value: Map coordinate in 0..800.

        Returns:
            Integer index in 0..CANVAS-1.
        """
        index = int(math.floor((value - ROAD_OFFSET) / (CELL_SIZE / 2) + 0.5))
        return min(max(index, 0), CANVAS - 1)

    @staticmethod
    def _base_symbol(row, col):
        """Return the default symbol for a canvas cell.

        Args:
            row: Canvas row index.
            col: Canvas column index.

        Returns:
            Symbol for an intersection, street segment or empty block.
        """
        if row % 2 == 0 and col % 2 == 0:
            return SYM_NODE
        if row % 2 == 0:
            return SYM_H_STREET
        if col % 2 == 0:
            return SYM_V_STREET
        return SYM_EMPTY

    def _draw_segment(self, canvas, a, b):
        """Draw a straight route segment between two map points.

        Args:
            canvas: 2D list of canvas symbols (modified in place).
            a: Start point ``(x, y)``.
            b: End point ``(x, y)``.
        """
        row_a, col_a = self._canvas_index(a[1]), self._canvas_index(a[0])
        row_b, col_b = self._canvas_index(b[1]), self._canvas_index(b[0])
        if row_a == row_b:
            for col in range(min(col_a, col_b), max(col_a, col_b) + 1):
                canvas[row_a][col] = SYM_ROUTE
        elif col_a == col_b:
            for row in range(min(row_a, row_b), max(row_a, row_b) + 1):
                canvas[row][col_a] = SYM_ROUTE

    def render_map(self, route=None):
        """Render the 8x8 ASCII map with riders, places and an optional route.

        Legend: ``+`` intersection, ``-``/``|`` streets, ``R`` restaurant,
        ``C`` customer, ``@`` rider, ``*`` planned route.

        Args:
            route: Optional list of ``(x, y)`` waypoints to draw.

        Returns:
            Multi-line string containing the map.
        """
        canvas = [
            [self._base_symbol(r, c) for c in range(CANVAS)]
            for r in range(CANVAS)
        ]
        if route:
            for a, b in zip(route, route[1:]):
                self._draw_segment(canvas, a, b)
        for x, y in sorted(get_value("restaurants") or set()):
            canvas[self._canvas_index(y)][self._canvas_index(x)] = SYM_RESTAURANT
        for x, y in sorted(get_value("customers") or set()):
            canvas[self._canvas_index(y)][self._canvas_index(x)] = SYM_CUSTOMER
        for rider in get_value("riders") or []:
            canvas[self._canvas_index(rider.y)][self._canvas_index(rider.x)] = SYM_RIDER

        lines = ["     " + " ".join(str(c // 2) if c % 2 == 0 else " " for c in range(CANVAS))]
        for r in range(CANVAS):
            if r % 2 == 0:
                label = f"{(r // 2) * CELL_SIZE + ROAD_OFFSET:>4} "
            else:
                label = " " * 5
            lines.append(label + " ".join(canvas[r]))
        lines.append("Legend: + intersection  - | street  R restaurant  C customer  @ rider  * route")
        lines.append("Columns/rows show cell index 0-7 (x/y centres 50..750).")
        return "\n".join(lines)

    def render_status(self):
        """Return the system status snapshot.

        Returns:
            Multi-line string with funds, tick, and every rider's details.
        """
        riders = get_value("riders") or []
        lines = [
            f"System funds: {get_value('funds', 0)}",
            f"Simulated tick: {get_value('tick', 0)}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} location=({rider.x},{rider.y}) "
                f"status={STATE_NAMES[rider.state]:<10} speed={rider.speed} "
                f"orders={len(rider.orders)} {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Return a table with details for each order.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line string table.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>5} {'Time':>5} {'Rider':>6} {'Status':<12}"
        )
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = o.time_taken()
            taken_text = str(taken) if taken is not None else "-"
            rider_text = f"#{o.rider_id}" if o.rider_id is not None else "-"
            lines.append(
                f"{o.id:>4} {o.created_tick:>6} {str(o.res_pos):>12} {str(o.cus_pos):>12} "
                f"{o.distance:>5} {taken_text:>5} {rider_text:>6} {o.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_logs(self):
        """Return every status-change record for all riders.

        Returns:
            Multi-line string with one line per logged event.
        """
        riders = get_value("riders") or []
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order_text = f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
                lines.append(
                    f"  t={entry['time']:>4} {entry['event']:<20} {order_text:<12} "
                    f"at ({entry['x']},{entry['y']}) state={STATE_NAMES[entry['state']]}"
                )
        return "\n".join(lines) if lines else "No rider activity recorded."

    @staticmethod
    def format_event(entry):
        """Format a single rider log entry for live output.

        Args:
            entry: Rider log dictionary.

        Returns:
            Human-readable one-line description.
        """
        order_text = f" (order #{entry['order_id']})" if entry["order_id"] is not None else ""
        return f"[t={entry['time']}] Rider #{entry['rider_id']}: {entry['event']}{order_text}"

    @staticmethod
    def help_text():
        """Return the command help text."""
        return HELP_TEXT
