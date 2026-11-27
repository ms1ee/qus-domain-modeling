"""Status displays and ASCII map rendering."""

from typing import Iterable, List, Optional, Sequence, Tuple

from grid import POINT_STEP, Grid
from rider import Rider

Point = Tuple[int, int]


class DisplayManager:
    """Renders maps, status tables and logs as text.

    Attributes:
        grid: Map description.
        symbol_map: Symbols used on the ASCII map.
    """

    def __init__(self, grid: Optional[Grid] = None) -> None:
        """Create a display manager.

        Args:
            grid: Map description; a default 800x800 grid when omitted.
        """
        self.grid = grid or Grid()
        self.symbol_map = {
            "empty": "+",
            "street_h": "-",
            "street_v": "|",
            "block": " ",
            "restaurant": "R",
            "customer": "C",
            "route": "*",
        }

    def _size(self) -> int:
        """Return the canvas dimension (one character per 50 units).

        Returns:
            int: Number of rows/columns on the canvas.
        """
        return self.grid.map_size // POINT_STEP + 1

    def _base_canvas(self) -> List[List[str]]:
        """Build the empty street canvas.

        Returns:
            List[List[str]]: 2D character grid.
        """
        n = self._size()
        canvas = [[" "] * n for _ in range(n)]
        for row in range(n):
            for col in range(n):
                x, y = col * POINT_STEP, row * POINT_STEP
                if self.grid.is_location(x, y):
                    key = "empty"
                elif self.grid.is_horizontal_street(y):
                    key = "street_h"
                elif self.grid.is_vertical_street(x):
                    key = "street_v"
                else:
                    key = "block"
                canvas[row][col] = self.symbol_map[key]
        return canvas

    def _cell(self, point: Point) -> Tuple[int, int]:
        """Convert a coordinate to canvas (row, col).

        Args:
            point: (x, y) coordinate.

        Returns:
            Tuple[int, int]: (row, col) index.
        """
        return point[1] // POINT_STEP, point[0] // POINT_STEP

    def _overlay_route(self, canvas: List[List[str]], waypoints: Sequence[Point]) -> None:
        """Mark route segments on the canvas with the route symbol.

        Args:
            canvas: Canvas to modify in place.
            waypoints: Ordered route corners.

        Returns:
            None
        """
        symbol = self.symbol_map["route"]
        cells = [(x // POINT_STEP, y // POINT_STEP) for x, y in waypoints]
        for (c1, r1), (c2, r2) in zip(cells, cells[1:]):
            if r1 == r2:
                targets = [(r1, c) for c in range(min(c1, c2), max(c1, c2) + 1)]
            elif c1 == c2:
                targets = [(r, c1) for r in range(min(r1, r2), max(r1, r2) + 1)]
            else:
                continue
            for r, c in targets:
                if canvas[r][c] in ("-", "|", "+"):
                    canvas[r][c] = symbol

    def _put(self, canvas: List[List[str]], point: Point, symbol: str) -> None:
        """Place a symbol at a coordinate if it lies on the canvas.

        Args:
            canvas: Canvas to modify.
            point: (x, y) coordinate.
            symbol: Character to place.

        Returns:
            None
        """
        row, col = self._cell(point)
        if 0 <= row < len(canvas) and 0 <= col < len(canvas[0]):
            canvas[row][col] = symbol

    def _format(self, canvas: List[List[str]]) -> str:
        """Convert the canvas to text with y-axis labels.

        Args:
            canvas: Character grid.

        Returns:
            str: Multi-line map text.
        """
        lines = []
        for row_index, row in enumerate(canvas):
            y = row_index * POINT_STEP
            label = f"{y:>3} " if y % self.grid.cell_size == 0 else "    "
            lines.append(label + " ".join(row))
        lines.append("    x: 0 .. %d (lattice every %d units)" % (
            self.grid.map_size, self.grid.cell_size))
        return "\n".join(lines)

    def render_map(
        self,
        riders: Iterable[Rider],
        orders: Iterable = (),
        route=None,
    ) -> str:
        """Render riders, active orders and an optional route on the map.

        Args:
            riders: Riders to draw (digit = rider ID mod 10).
            orders: Orders whose restaurants (R) and customers (C) are drawn.
            route: Optional Route to highlight with ``*``.

        Returns:
            str: ASCII map.
        """
        canvas = self._base_canvas()
        if route is not None:
            self._overlay_route(canvas, route.waypoints)
        for order in orders:
            if order.is_completed():
                continue
            self._put(canvas, order.res_pos, self.symbol_map["restaurant"])
            self._put(canvas, order.cus_pos, self.symbol_map["customer"])
        for rider in riders:
            self._put(canvas, rider.position, str(rider.rider_id % 10))
        return self._format(canvas)

    def render_legend(self) -> str:
        """Return the map legend.

        Returns:
            str: Legend text.
        """
        return (
            "Legend: + intersection  - | street  R restaurant  C customer  "
            "* route  0-9 rider (id mod 10)"
        )

    def render_status(self, system) -> str:
        """Render a snapshot of funds, clock and all riders.

        Args:
            system: SystemManager instance.

        Returns:
            str: Status text.
        """
        lines = [
            f"Tick: {system.current_tick}",
            f"System funds: {system.funds}",
            f"Riders: {len(system.riders)} (max {system.max_riders})",
            f"Active orders: {len(system.order_manager.active_orders())}",
        ]
        for rider in system.riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={rider.state_name} orders={len(rider.orders)} "
                f"order_ids={order_ids}"
            )
        if not system.riders:
            lines.append("  No riders on duty.")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Render a table of order details.

        Args:
            orders: Orders to show.

        Returns:
            str: Table text.
        """
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>6} {'Time':>6} {'Rider':>6} {'Status':<12}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            time_taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} "
                f"{str(order.res_pos):>12} {str(order.cus_pos):>12} "
                f"{order.distance:>6} {time_taken:>6} {rider:>6} {order.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Iterable[Rider]) -> str:
        """Render the status-change history of every rider.

        Args:
            riders: Riders whose logs should be shown.

        Returns:
            str: Log text.
        """
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else entry["order_id"]
                lines.append(
                    f"  t={entry['tick']:>5} {entry['event']:<22} order={order} "
                    f"pos=({entry['x']}, {entry['y']}) state={entry['state']}"
                )
        return "\n".join(lines) if lines else "No riders."

    def render_order_summary(self, result: dict) -> str:
        """Render the summary of a newly submitted order.

        Args:
            result: Dictionary returned by ``SystemManager.submit_order``.

        Returns:
            str: Summary text.
        """
        order = result["order"]
        rider = result["rider"]
        route = result["route"]
        route_text = " -> ".join(str(point) for point in route.waypoints)
        lines = [
            f"Order #{order.id} accepted.",
            f"Restaurant grid location: {order.res_pos}",
            f"Customer grid location:   {order.cus_pos}",
            f"Distance: {order.distance} units",
            f"Assigned rider: #{rider.rider_id} (speed {rider.speed} units/tick)",
            f"New rider recruited: {'yes' if result['new_rider'] else 'no'}",
            f"Estimated time: {route.estimated_time} tick(s)",
            f"Route: {route_text}",
        ]
        return "\n".join(lines)
