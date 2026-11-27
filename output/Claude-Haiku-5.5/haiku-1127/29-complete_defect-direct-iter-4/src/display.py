"""Status displays and ASCII map rendering.

The ASCII map has 17x17 characters. One character equals 50 units, so every
street line (multiple of 100) sits on an even index and every cell center
(50 + 100k) sits on an odd index. Row 0 is the top of the map (y = 800).
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from path_planner import GRID_SIZE, grid_cell
from rider import STATE_NAMES

MAP_UNIT = 50
MAP_SIZE = GRID_SIZE // MAP_UNIT + 1  # 17 characters per side
Point = Tuple[int, int]


def _to_index(value: int) -> int:
    """Convert a coordinate into a map character index."""
    return min(max(int(value) // MAP_UNIT, 0), MAP_SIZE - 1)


def _segment_points(a: Point, b: Point) -> List[Point]:
    """Sample points along an axis-aligned segment from a to b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    total = abs(dx) + abs(dy)
    points: List[Point] = []
    for i in range(0, total + 1, 10):
        x = ax + sx * min(i, abs(dx))
        y = ay + sy * min(max(i - abs(dx), 0), abs(dy))
        points.append((x, y))
    points.append((bx, by))
    return points


class DisplayManager:
    """Renders the map and formats status tables for the console."""

    LEGEND = "R=Rider  S=Restaurant  C=Customer  #=street  .=empty  *=planned route"

    def render_map(self, riders: Iterable[Any] = (), orders: Iterable[Any] = (),
                   route: Optional[Sequence[Point]] = None) -> str:
        """Render the ASCII map with riders, active orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are shown
                while they are not completed.
            route: Optional waypoint list drawn as a connected line ('*').

        Returns:
            The multi-line map text.
        """
        canvas = [
            ["#" if (row % 2 == 0 or col % 2 == 0) else "." for col in range(MAP_SIZE)]
            for row in range(MAP_SIZE)
        ]
        if route:
            for a, b in zip(route, route[1:]):
                for point in _segment_points(a, b):
                    self._plot(canvas, point, "*")
            self._plot(canvas, route[0], "*")
        for order in orders:
            if order.status == "completed":
                continue
            self._plot(canvas, order.res_pos, "S")
            self._plot(canvas, order.cus_pos, "C")
        for rider in riders:
            self._plot(canvas, rider.position, "R")

        lines = []
        for row in range(MAP_SIZE):
            y_value = (MAP_SIZE - 1 - row) * MAP_UNIT
            label = f"{y_value:>4} " if row % 2 == 0 else "     "
            lines.append(label + " ".join(canvas[row]))
        lines.append(self.LEGEND)
        lines.append("x: 0 (left) .. 800 (right); one character = 50 units; "
                     "streets at multiples of 100")
        return "\n".join(lines)

    @staticmethod
    def _plot(canvas: List[List[str]], point: Point, symbol: str) -> None:
        """Place a symbol on the canvas, respecting display priorities."""
        col = _to_index(point[0])
        row = MAP_SIZE - 1 - _to_index(point[1])
        if symbol == "*" and canvas[row][col] in ("R", "S", "C"):
            return
        canvas[row][col] = symbol

    def format_status(self, funds: int, current_time: int, riders: Sequence[Any],
                      active_orders: int, completed_orders: int) -> str:
        """Format the system snapshot shown by the 'status' command."""
        lines = [
            f"System status at t={current_time}",
            f"Funds: {funds}",
            f"Riders: {len(riders)}",
            f"Orders: {active_orders} active, {completed_orders} completed",
        ]
        for rider in riders:
            cell = grid_cell(rider.position)
            order_ids = [order.id for order in rider.orders] or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: {rider.state_name} | cell {cell} "
                f"at ({rider.x},{rider.y}) | speed {rider.speed} | "
                f"orders: {order_ids}"
            )
        return "\n".join(lines)

    def format_orders(self, orders: Sequence[Any]) -> str:
        """Format the order table shown by the 'orders' command."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>16} {'Customer':>16} "
                  f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            taken = "-" if order.time_taken is None else str(order.time_taken)
            rider = "-" if order.rider_id is None else f"#{order.rider_id}"
            lines.append(
                f"{order.id:>4} {order.start_tick:>6} "
                f"{str(order.restaurant_cell):>16} {str(order.customer_cell):>16} "
                f"{order.distance:>6} {taken:>6} {rider:>6} {order.status:>10}"
            )
        return "\n".join(lines)

    def format_riders(self, riders: Sequence[Any]) -> str:
        """Format the full status change history of all riders."""
        if not riders:
            return "No riders have been recruited yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id} (speed {rider.speed}):")
            if not rider.history:
                lines.append("  (no records)")
            for entry in rider.history:
                lines.append("  " + self._format_entry(entry))
        return "\n".join(lines)

    def format_events(self, events: Sequence[dict]) -> str:
        """Format a list of history entries produced during a tick."""
        if not events:
            return "No rider status changes."
        return "\n".join("  " + self._format_entry(e) for e in events)

    @staticmethod
    def _format_entry(entry: dict) -> str:
        """Format one rider history record as a single line."""
        order = "-" if entry["order_id"] is None else f"order #{entry['order_id']}"
        state = STATE_NAMES.get(entry["state"], "unknown")
        return (f"t={entry['time']:<4} rider #{entry['rider_id']:<3} "
                f"{entry['event']:<22} {order:<12} at ({entry['x']},{entry['y']}) "
                f"state={state}")
