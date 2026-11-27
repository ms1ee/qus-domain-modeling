"""Status display and ASCII map rendering."""

from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from config import (CELL_SIZE, GRID_DIMENSION, MAP_SIZE, ORDER_COMPLETED,
                    STATE_NAMES)

SAMPLE_STEP = 50  # One map character represents 50 units (17x17 points).
Point = Tuple[int, int]


class DisplayManager:
    """Render system status, order tables, rider logs and the ASCII map.

    Map symbols:
        'R' rider, 'S' restaurant, 'C' customer, '.' empty,
        '#' street, '*' planned route.
    """

    def __init__(self, map_dimension: int = GRID_DIMENSION) -> None:
        """Create the display manager.

        Args:
            map_dimension: Number of grid cells per side.
        """
        self.map_dimension = map_dimension
        self.sample_count = MAP_SIZE // SAMPLE_STEP + 1

    # ------------------------------------------------------------------
    # Map
    # ------------------------------------------------------------------
    def render_map(self, riders: Iterable = (), orders: Iterable = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Return an ASCII map of riders, active orders and an optional route.

        Args:
            riders: Riders to plot as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') positions
                are plotted if they are not completed.
            route: Optional list of corner points drawn as '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        n = self.sample_count
        canvas = [["." for _ in range(n)] for _ in range(n)]
        for row in range(n):
            for col in range(n):
                x = col * SAMPLE_STEP
                y = row * SAMPLE_STEP
                if x % CELL_SIZE == 0 or y % CELL_SIZE == 0:
                    canvas[row][col] = "#"

        if route:
            for a, b in zip(route, route[1:]):
                for px, py in _segment_points(a, b):
                    _put(canvas, px, py, "*")

        for order in orders:
            if order.status == ORDER_COMPLETED:
                continue
            _put(canvas, order.res_pos[0], order.res_pos[1], "S")
            _put(canvas, order.cus_pos[0], order.cus_pos[1], "C")

        for rider in riders:
            _put(canvas, rider.x, rider.y, "R")

        lines = ["".join(row) for row in canvas]
        legend = ("Legend: R rider  S restaurant  C customer  "
                  "# street  * route  . empty  (1 char = 50 units, "
                  "origin top-left)")
        return "\n".join(lines) + "\n" + legend

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    def render_status(self, funds: int, riders: Sequence,
                      pending_count: int = 0) -> str:
        """Return the system status snapshot as text."""
        lines = [
            "=== System Status ===",
            f"Funds: {funds}",
            f"Pending orders: {pending_count}",
            f"Riders: {len(riders)}",
        ]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            active = rider.active_orders
            active_ids = ", ".join(str(o.id) for o in active) or "-"
            lines.append(
                f"  Rider {rider.rider_id} | position ({rider.x}, {rider.y}) | "
                f"state: {STATE_NAMES.get(rider.state, rider.state)} | "
                f"assigned orders: {len(rider.orders)} "
                f"(active: {active_ids})")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Return a table of all orders with timing and assignment data."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Distance':>9} {'Time':>6} {'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for o in orders:
            rider = o.rider_id if o.rider_id is not None else "-"
            time_taken = o.time_taken if o.time_taken is not None else "-"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str(o.res_pos):>12} "
                f"{str(o.cus_pos):>12} {o.distance:>9} {str(time_taken):>6} "
                f"{str(rider):>6} {o.status:>10}")
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence) -> str:
        """Return the status-change history for every rider."""
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"  t={entry['time']:>4} | {entry['event']:<20} | "
                    f"order={order} | pos=({entry['x']}, {entry['y']}) | "
                    f"state={STATE_NAMES.get(entry['state'], entry['state'])}")
        return "\n".join(lines)


def _put(canvas: List[List[str]], x: int, y: int, symbol: str) -> None:
    """Place ``symbol`` on the canvas at the sample nearest to ``(x, y)``."""
    n = len(canvas)
    col = min(max((int(x) + SAMPLE_STEP // 2) // SAMPLE_STEP, 0), n - 1)
    row = min(max((int(y) + SAMPLE_STEP // 2) // SAMPLE_STEP, 0), n - 1)
    canvas[row][col] = symbol


def _segment_points(a: Point, b: Point) -> Iterator[Point]:
    """Yield sample points along the straight segment from ``a`` to ``b``."""
    dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
    steps = max(1, dist // SAMPLE_STEP)
    for i in range(steps + 1):
        yield (a[0] + (b[0] - a[0]) * i // steps,
               a[1] + (b[1] - a[1]) * i // steps)
