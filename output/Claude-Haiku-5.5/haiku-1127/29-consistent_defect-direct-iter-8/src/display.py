"""Status displays and ASCII map visualisation.

Map legend:
    '#' street, '.' empty block interior, 'S' restaurant, 'C' customer,
    'R' rider, '*' planned route.

The 800x800 map is sampled every 50 units, giving a 17x17 character canvas
(9 street lines per axis, including both edges). Streets lie on even canvas
rows/columns, which corresponds to the 100-unit grid lines.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from order_model import COMPLETED, Order
from path_planner import MAP_SIZE, Point, estimate_ticks, route_length
from rider import STATE_NAMES, Rider

SAMPLE_STEP = 50
CANVAS_SIZE = MAP_SIZE // SAMPLE_STEP + 1  # 17


class DisplayManager:
    """Renders status tables, logs and the command-line map."""

    # ------------------------------------------------------------------ #
    # Map rendering
    # ------------------------------------------------------------------ #
    @staticmethod
    def _cell(x: int, y: int) -> Tuple[int, int]:
        """Map a coordinate to canvas ``(row, col)``."""
        col = min(CANVAS_SIZE - 1, max(0, round(x / SAMPLE_STEP)))
        row = min(CANVAS_SIZE - 1, max(0, round(y / SAMPLE_STEP)))
        return row, col

    def render_map(
        self,
        riders: Iterable[Rider],
        orders: Iterable[Order] = (),
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to draw as 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are drawn.
                Completed orders are skipped.
            route: Optional polyline of points drawn with '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        n = CANVAS_SIZE
        canvas = [
            ["#" if (row % 2 == 0 or col % 2 == 0) else "." for col in range(n)]
            for row in range(n)
        ]

        if route:
            for a, b in zip(route, route[1:]):
                self._draw_segment(canvas, a, b)

        for order in orders:
            if order.status == COMPLETED:
                continue
            r, c = self._cell(*order.res_pos)
            canvas[r][c] = "S"
            r, c = self._cell(*order.cus_pos)
            canvas[r][c] = "C"

        for rider in riders:
            r, c = self._cell(rider.x, rider.y)
            canvas[r][c] = "R"

        lines = ["".join(row) for row in canvas]
        legend = (
            "Legend: R=rider  S=restaurant  C=customer  #=street  "
            ".=empty  *=route   (1 char = 50 units, streets every 100)"
        )
        return "\n".join(lines + [legend])

    def _draw_segment(self, canvas: List[List[str]], a: Point, b: Point) -> None:
        """Mark an axis-aligned route segment with '*' on the canvas."""
        xs = range(min(a[0], b[0]), max(a[0], b[0]) + 1, SAMPLE_STEP)
        ys = range(min(a[1], b[1]), max(a[1], b[1]) + 1, SAMPLE_STEP)
        for x in xs:
            for y in ys:
                r, c = self._cell(x, y)
                if canvas[r][c] not in ("S", "C", "R"):
                    canvas[r][c] = "*"

    # ------------------------------------------------------------------ #
    # Text tables
    # ------------------------------------------------------------------ #
    def render_status(self, riders: Sequence[Rider], pending_count: int) -> str:
        """Render a per-rider status snapshot.

        Args:
            riders: All riders.
            pending_count: Number of orders waiting for a rider.

        Returns:
            Multi-line status text.
        """
        lines = [f"Riders on duty: {len(riders)}"]
        if not riders:
            lines.append("  (no riders recruited yet)")
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} at ({rider.x:>3},{rider.y:>3})  "
                f"state: {rider.state_name:<11} "
                f"active orders: {len(rider.active_orders()):<2} "
                f"order list: {order_ids}"
            )
        lines.append(f"Pending (unassigned) orders: {pending_count}")
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Order]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Formatted table text.
        """
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
            f"{'Dist':>6} {'Time':>6} {'Rider':>6} {'Status':<12}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            restaurant = f"({order.res_pos[0]},{order.res_pos[1]})"
            customer = f"({order.cus_pos[0]},{order.cus_pos[1]})"
            time_text = str(order.time_taken) if order.time_taken is not None else "-"
            rider_text = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {restaurant:>12} {customer:>12} "
                f"{order.distance:>6} {time_text:>6} {rider_text:>6} {order.status:<12}"
            )
        return "\n".join(lines)

    def render_rider_log(self, riders: Sequence[Rider]) -> str:
        """Render every recorded status change for every rider.

        Args:
            riders: Riders whose logs are shown.

        Returns:
            Multi-line log text.
        """
        if not riders:
            return "No riders."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed} units/tick):")
            for entry in rider.log:
                order_text = (
                    f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
                )
                state_text = STATE_NAMES.get(entry["state"], "unknown")
                lines.append(
                    f"  t={entry['time']:>5}  {entry['event']:<20} {order_text:<12} "
                    f"location=({entry['x']},{entry['y']})  state={state_text}"
                )
        return "\n".join(lines)

    def render_route(self, points: Sequence[Point], speed: int) -> str:
        """Describe a planned route with its length and estimated time.

        Args:
            points: Route polyline.
            speed: Rider speed in units per tick.

        Returns:
            Multi-line route description.
        """
        length = route_length(points)
        path_text = " -> ".join(f"({x},{y})" for x, y in points)
        return (
            f"Route: {path_text}\n"
            f"Route length: {length} units | speed: {speed} units/tick | "
            f"estimated time: {estimate_ticks(length, speed)} ticks"
        )
