"""Status display, order/rider reports and ASCII map rendering.

Map layout: the 800x800 map is drawn on a 17x17 character canvas. Each
character covers 50 units, so grid nodes (multiples of 100) fall on even
rows and columns. Symbols:
    '#'  street (grid line)          '.'  empty cell interior
    'S'  restaurant (active order)   'C'  customer (active order)
    'R'  rider                       '*'  planned route
"""

from order_model import ORDER_COMPLETED
from rider import STATE_NAMES

CANVAS_SIZE = 17
CELL_UNITS = 50
MAX_CELL_INDEX = CANVAS_SIZE - 1


def _segment_points(start, end):
    """Return sample points along an axis-aligned segment, including ends."""
    if start[0] == end[0]:
        low, high = sorted((start[1], end[1]))
        points = [(start[0], v) for v in range(low, high + 1, 10)]
        points.append((start[0], high))
    elif start[1] == end[1]:
        low, high = sorted((start[0], end[0]))
        points = [(v, start[1]) for v in range(low, high + 1, 10)]
        points.append((high, start[1]))
    else:
        points = [tuple(start), tuple(end)]
    return points


def _format_table(headers, rows):
    """Format rows into an aligned text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
    return "\n".join(lines)


class DisplayManager:
    """Renders status screens and the command-line map."""

    LEGEND = (
        "Legend: R=Rider  S=Restaurant  C=Customer  #=Street  "
        ".=Empty  *=Route\n"
        "Grid nodes are every 100 units; labels show node indices (0-8)."
    )

    @staticmethod
    def _cell(x, y):
        """Map a coordinate to a canvas ``(row, col)`` pair."""
        col = min(int(x) // CELL_UNITS, MAX_CELL_INDEX)
        row = min(int(y) // CELL_UNITS, MAX_CELL_INDEX)
        return row, col

    def _put(self, canvas, point, symbol):
        """Place a symbol on the canvas at ``point``."""
        row, col = self._cell(point[0], point[1])
        canvas[row][col] = symbol

    def render_map(self, riders=(), orders=(), route=None):
        """Render the ASCII map with riders, active orders and an optional route.

        Args:
            riders: Iterable of riders to mark with 'R'.
            orders: Iterable of orders; non-completed ones are marked 'S'/'C'.
            route: Optional list of ``(x, y)`` points drawn with '*'.

        Returns:
            Multi-line string of the map with labels.
        """
        canvas = [
            ["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(CANVAS_SIZE)]
            for r in range(CANVAS_SIZE)
        ]
        if route and len(route) > 1:
            for start, end in zip(route, route[1:]):
                for point in _segment_points(start, end):
                    self._put(canvas, point, "*")
        for order in orders:
            if order.status == ORDER_COMPLETED:
                continue
            self._put(canvas, order.res_pos, "S")
            self._put(canvas, order.cus_pos, "C")
        for rider in riders:
            self._put(canvas, (rider.x, rider.y), "R")

        ruler = "   " + "".join(
            str(c // 2) if c % 2 == 0 else " " for c in range(CANVAS_SIZE)
        )
        lines = [ruler]
        for r, row in enumerate(canvas):
            label = f"{r // 2:>2} " if r % 2 == 0 else "   "
            lines.append(label + "".join(row))
        return "\n".join(lines)

    def legend(self):
        """Return the map legend text."""
        return self.LEGEND

    def show_map(self, riders=(), orders=(), route=None):
        """Print the rendered map followed by the legend."""
        print(self.render_map(riders, orders, route))
        print(self.legend())

    def show_status(self, funds, riders, pending, issues=()):
        """Print the system snapshot: funds, riders and consistency result.

        Args:
            funds: Current system funds.
            riders: List of riders.
            pending: Number of pending (unassigned) orders.
            issues: Consistency issues reported by the system.
        """
        print("=== System Status ===")
        print(f"System funds   : {funds}")
        print(f"Rider count    : {len(riders)}")
        print(f"Pending orders : {pending}")
        for rider in riders:
            active = rider.active_orders()
            ids = ", ".join(f"#{o.id}" for o in active) or "-"
            print(
                f"  Rider #{rider.rider_id:<3} pos=({rider.x},{rider.y})  "
                f"status={STATE_NAMES.get(rider.state, 'Unknown'):<11} "
                f"active orders={len(active)} [{ids}]  "
                f"history={len(rider.orders)}"
            )
        if issues:
            print("Consistency issues:")
            for issue in issues:
                print(f"  ! {issue}")
        else:
            print("Consistency check: OK")

    def show_orders(self, orders):
        """Print a table of all orders.

        Args:
            orders: Iterable of ``Order`` objects.
        """
        orders = list(orders)
        if not orders:
            print("No orders yet.")
            return
        headers = ["ID", "Start", "Restaurant", "Customer", "Distance",
                   "Time", "Rider", "Status"]
        rows = []
        for o in orders:
            rows.append([
                o.id,
                o.created_tick,
                f"{o.res_pos[0]},{o.res_pos[1]}",
                f"{o.cus_pos[0]},{o.cus_pos[1]}",
                o.distance,
                o.time_taken if o.time_taken is not None else "-",
                f"#{o.rider_id}" if o.rider_id is not None else "-",
                o.status,
            ])
        print(_format_table(headers, rows))

    def show_rider_history(self, riders):
        """Print every recorded status-change event for all riders.

        Args:
            riders: Iterable of ``Rider`` objects.
        """
        riders = list(riders)
        if not riders:
            print("No riders have been recruited yet.")
            return
        for rider in riders:
            print(f"--- Rider #{rider.rider_id} ---")
            for entry in rider.log:
                order_text = f"order #{entry['order_id']}" if entry["order_id"] else "-"
                print(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22} | "
                    f"{order_text:<10} | pos ({entry['x']},{entry['y']}) | "
                    f"{STATE_NAMES.get(entry['state'], 'Unknown')}"
                )

    def show_route(self, rider, order, route, ticks):
        """Print the route summary and map for a newly assigned order.

        Args:
            rider: The assigned ``Rider``.
            order: The ``Order`` that was assigned.
            route: List of ``(x, y)`` route points.
            ticks: Estimated travel time in ticks.
        """
        print(f"Route for Rider #{rider.rider_id}: speed {rider.speed} units/tick, "
              f"estimated time {ticks} tick(s)")
        print("Waypoints: " + " -> ".join(f"({x},{y})" for x, y in route))
        self.show_map([rider], [order], route)

    def show_message(self, text):
        """Print an informational message."""
        print(text)

    def show_error(self, text):
        """Print an error message prefixed for visibility."""
        print(f"[Error] {text}")
