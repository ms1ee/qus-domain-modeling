"""Status displays and ASCII map visualisation.

The map is drawn on a character canvas where every routing-lattice node
(every 50 units) occupies one even-indexed cell and the space between two
neighbouring nodes is an odd-indexed cell. This makes streets and route
segments visible as connected lines.

Symbols:
    R  rider          S  restaurant      C  customer
    .  empty space    #  street          *  route node
    -  route segment (horizontal)        |  route segment (vertical)
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from grid import CELL_SIZE, LATTICE_STEP, MAP_SIZE
from path_planner import Route

Point = Tuple[int, int]

LEGEND = ("Legend: R rider  S restaurant  C customer  # street  . block  "
          "* route  -/| route segment\n"
          "Top = y 800, left = x 0. Streets are the lines at multiples of 100; "
          "cell centres are at 50, 150, ... 750.")


class DisplayManager:
    """Renders the map, status, order table and rider logs as text."""

    def __init__(self, map_width: int = MAP_SIZE, map_height: int = MAP_SIZE,
                 cell_size: int = CELL_SIZE) -> None:
        """Create a display manager.

        Args:
            map_width: Map width in units.
            map_height: Map height in units.
            cell_size: Grid cell size in units.
        """
        self.map_width = map_width
        self.map_height = map_height
        self.cell_size = cell_size
        self.step = LATTICE_STEP

    def _to_canvas(self, x: float, y: float) -> Tuple[int, int]:
        """Convert map coordinates to (row, column) canvas indices."""
        col = int(round(2 * x / self.step))
        row = int(round(2 * (self.map_height - y) / self.step))
        return row, col

    def _is_street(self, x: int, y: int) -> bool:
        """Return True if the lattice node lies on a street."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def render_map(self, riders: Iterable = (), orders: Iterable = (),
                   route: Optional[Route] = None) -> str:
        """Render the 8x8 city map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are shown.
            route: Optional route drawn as connected line segments.

        Returns:
            The map as a multi-line string.
        """
        rows = 2 * self.map_height // self.step + 1
        cols = 2 * self.map_width // self.step + 1
        canvas: List[List[str]] = [["." for _ in range(cols)] for _ in range(rows)]
        nodes_x = self.map_width // self.step + 1
        nodes_y = self.map_height // self.step + 1

        for xi in range(nodes_x):
            for yi in range(nodes_y):
                x, y = xi * self.step, yi * self.step
                row, col = self._to_canvas(x, y)
                if self._is_street(x, y):
                    canvas[row][col] = "#"
                if xi + 1 < nodes_x and y % self.cell_size == 0:
                    r2, c2 = self._to_canvas(x + self.step, y)
                    canvas[(row + r2) // 2][(col + c2) // 2] = "#"
                if yi + 1 < nodes_y and x % self.cell_size == 0:
                    r2, c2 = self._to_canvas(x, y + self.step)
                    canvas[(row + r2) // 2][(col + c2) // 2] = "#"

        if route is not None:
            points = list(route.points)
            for a, b in zip(points, points[1:]):
                ra, ca = self._to_canvas(*a)
                rb, cb = self._to_canvas(*b)
                canvas[(ra + rb) // 2][(ca + cb) // 2] = "-" if a[1] == b[1] else "|"
            for point in points:
                r, c = self._to_canvas(*point)
                canvas[r][c] = "*"

        for order in orders:
            r, c = self._to_canvas(order.restaurant_x, order.restaurant_y)
            canvas[r][c] = "S"
            r, c = self._to_canvas(order.customer_x, order.customer_y)
            canvas[r][c] = "C"

        for rider in riders:
            r, c = self._to_canvas(rider.x, rider.y)
            canvas[r][c] = "R"

        body = "\n".join("".join(row) for row in canvas)
        return f"{body}\n{LEGEND}"

    @staticmethod
    def _cell_label(x: int, y: int) -> str:
        """Return the grid cell label of a coordinate, e.g. '(1,2)'."""
        gx = min(max(x // CELL_SIZE, 0), 7)
        gy = min(max(y // CELL_SIZE, 0), 7)
        return f"({gx},{gy})"

    def render_status(self, system) -> str:
        """Render funds, rider count and per-rider details.

        Args:
            system: SystemManager instance.
        """
        lines = [
            f"Simulated time : {system.simulated_time}",
            f"System funds   : {system.funds}",
            f"Rider count    : {len(system.riders)}",
        ]
        for rider in system.riders:
            order_ids = ", ".join(str(getattr(o, "id", "?")) for o in rider.orders) or "-"
            order_status = ", ".join(
                f"#{o.id}:{o.status}" for o in rider.orders) or "-"
            lines.append(
                f"  Rider {rider.rider_id:>3} | {rider.state_name:<10} | "
                f"pos ({rider.x},{rider.y}) | cell {self._cell_label(rider.x, rider.y)} | "
                f"speed {rider.speed} | orders [{order_ids}] | {order_status}")
        if not system.riders:
            lines.append("  No riders yet. Riders are recruited when funds reach the threshold.")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Render a table of orders.

        Args:
            orders: Order objects to display.
        """
        if not orders:
            return "No orders have been placed yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Taken':>6} {'Rider':>6} {'Status':<12}")
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:>4} {o.start_time:>6} "
                f"{'(' + str(o.restaurant_x) + ',' + str(o.restaurant_y) + ')':>12} "
                f"{'(' + str(o.customer_x) + ',' + str(o.customer_y) + ')':>12} "
                f"{o.distance:>9} {taken:>6} {rider:>6} {o.status:<12}")
        return "\n".join(lines)

    def render_rider_log(self, riders: Sequence) -> str:
        """Render every recorded status change of every rider.

        Args:
            riders: Rider objects whose logs are shown.
        """
        if not riders:
            return "No riders yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} (current state: {rider.state_name})")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else str(entry["order_id"])
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<22} "
                    f"order={order:<5} pos=({entry['x']},{entry['y']})")
        return "\n".join(lines)
