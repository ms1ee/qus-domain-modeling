"""Status tables and ASCII map rendering."""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from order_model import MAP_SIZE
from path_planner import Point
from rider import Rider


class DisplayManager:
    """Builds textual status reports and the ASCII map.

    The map uses a 17x17 character canvas. Street intersections sit on even
    character indices (every 100 units), so the 8x8 cells are visible.

    Symbols:
        'R' rider, 'S' restaurant, 'C' customer, '#' street,
        '.' empty cell interior, '*' planned route.

    Attributes:
        map_rows: Number of character rows in the map.
        map_columns: Number of character columns in the map.
    """

    STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    def __init__(self, map_rows: int = 17, map_columns: int = 17) -> None:
        """Create a display manager.

        Args:
            map_rows: Rows in the ASCII map.
            map_columns: Columns in the ASCII map.
        """
        self.map_rows = map_rows
        self.map_columns = map_columns
        self._pixels_per_char = MAP_SIZE // (self.map_columns - 1) // 1

    def _to_cell(self, x: int, y: int) -> Tuple[int, int]:
        """Convert a coordinate to a (row, column) map position.

        Args:
            x: X coordinate in units.
            y: Y coordinate in units.

        Returns:
            (row, column) inside the character canvas.
        """
        step = MAP_SIZE // (self.map_columns - 1)
        col = min(self.map_columns - 1, max(0, x // step))
        row = min(self.map_rows - 1, max(0, y // step))
        return row, col

    def render_status(self, funds: int, time: int, riders: Sequence[Rider]) -> str:
        """Render a snapshot of funds, riders and their orders.

        Args:
            funds: Current system funds.
            time: Current simulation tick.
            riders: Riders to report.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"=== System Status (tick {time}) ===",
            f"Funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id} | position ({rider.x}, {rider.y}) | "
                f"state: {self.STATE_NAMES.get(rider.state, 'unknown')} | "
                f"active orders: {len(rider.active_orders())} | orders: {order_ids}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Any]) -> str:
        """Render a table of all orders.

        Args:
            orders: Order objects to display.

        Returns:
            Multi-line table text.
        """
        rows = ["ID | Start | Restaurant | Customer | Distance | Time | Rider | Status"]
        count = 0
        for o in orders:
            count += 1
            time_taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"#{o.rider_id}"
            rows.append(
                f"{o.id} | {o.start_time} | {o.restaurant_pos} | {o.customer_pos} | "
                f"{o.distance:.0f} | {time_taken} | {rider} | {o.status}"
            )
        if count == 0:
            rows.append("(no orders)")
        return "\n".join(rows)

    def render_rider_logs(self, riders: Sequence[Rider]) -> str:
        """Render the status-change history of every rider.

        Args:
            riders: Riders whose logs are displayed.

        Returns:
            Multi-line text.
        """
        if not riders:
            return "(no riders)"
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                lines.append(
                    f"  t={entry['time']:<5} {entry['event']:<22} order={order:<6} "
                    f"pos=({entry['x']}, {entry['y']}) "
                    f"state={self.STATE_NAMES.get(entry['state'], '?')}"
                )
        return "\n".join(lines)

    def _draw_route(self, canvas: List[List[str]], route: Sequence[Point]) -> None:
        """Draw connected street segments of a route onto the canvas.

        Args:
            canvas: Character canvas to modify in place.
            route: Ordered route points.
        """
        for (ax, ay), (bx, by) in zip(route, route[1:]):
            if ax == bx:
                for y in range(min(ay, by), max(ay, by) + 1):
                    row, col = self._to_cell(ax, y)
                    if canvas[row][col] in ("#", "."):
                        canvas[row][col] = "*"
            elif ay == by:
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    row, col = self._to_cell(x, ay)
                    if canvas[row][col] in ("#", "."):
                        canvas[row][col] = "*"

    def render_map(self, riders: Sequence[Rider], orders: Iterable[Any],
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the ASCII map with streets, riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurants ('S') and customers ('C') are shown.
                Completed orders are not shown.
            route: Optional route to draw as a connected line graph.

        Returns:
            Multi-line map text including a legend.
        """
        canvas = [["." for _ in range(self.map_columns)] for _ in range(self.map_rows)]
        for i in range(0, self.map_rows, 2):
            for j in range(self.map_columns):
                canvas[i][j] = "#"
                canvas[j][i] = "#"
        if route:
            self._draw_route(canvas, route)
        for o in orders:
            if o.status == "completed":
                continue
            r, c = self._to_cell(o.restaurant_x, o.restaurant_y)
            canvas[r][c] = "S"
            r, c = self._to_cell(o.customer_x, o.customer_y)
            canvas[r][c] = "C"
        for rider in riders:
            r, c = self._to_cell(rider.x, rider.y)
            canvas[r][c] = "R"
        body = ["".join(row) for row in canvas]
        body.append("Legend: R rider, S restaurant, C customer, # street, "
                    ". empty, * planned route")
        return "\n".join(body)
