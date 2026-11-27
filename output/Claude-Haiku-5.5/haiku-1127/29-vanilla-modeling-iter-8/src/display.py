"""Status display and ASCII map visualisation.

The map is rendered on a 17x17 character canvas: one character per 50
units, so that street grid lines (multiples of 100) and cell centres
(50, 150, ...) are both represented. Symbols: R rider, S restaurant,
C customer, '#' street, '.' empty cell interior, '*' planned route.
"""

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from path_planner import Route

Point = Tuple[int, int]

STATE_NAMES: Dict[int, str] = {0: "idle", 1: "picking up", 2: "delivering"}
RESOLUTION = 50
MAP_SIZE = 800
CANVAS_SIZE = MAP_SIZE // RESOLUTION + 1
SAMPLE_STEP = 10


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


class DisplayManager:
    """Produces text output for the command-line interface."""

    def __init__(self) -> None:
        """Create the display manager with its symbol mapping."""
        self.map_symbols: Dict[str, str] = {
            "rider": "R",
            "restaurant": "S",
            "customer": "C",
            "empty": ".",
            "street": "#",
            "route": "*",
        }

    # ------------------------------------------------------------------
    # Map
    # ------------------------------------------------------------------
    @staticmethod
    def _index(coord: int) -> int:
        return min(max(int(coord) // RESOLUTION, 0), CANVAS_SIZE - 1)

    def _blank_canvas(self) -> List[List[str]]:
        canvas: List[List[str]] = []
        for row in range(CANVAS_SIZE):
            line = []
            for col in range(CANVAS_SIZE):
                on_street = row % 2 == 0 or col % 2 == 0
                line.append(self.map_symbols["street"] if on_street
                            else self.map_symbols["empty"])
            canvas.append(line)
        return canvas

    def _place(self, canvas: List[List[str]], x: int, y: int, symbol: str) -> None:
        canvas[self._index(y)][self._index(x)] = symbol

    def _draw_route(self, canvas: List[List[str]], waypoints: Sequence[Point]) -> None:
        """Draw connected axis-aligned segments between waypoints."""
        symbol = self.map_symbols["route"]
        for start, end in zip(waypoints, waypoints[1:]):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = abs(dx) + abs(dy)
            for step in range(0, length + 1, SAMPLE_STEP):
                t = min(step, length)
                x = start[0] + _sign(dx) * min(t, abs(dx))
                y = start[1] + _sign(dy) * min(t, abs(dy))
                self._place(canvas, x, y, symbol)
            self._place(canvas, end[0], end[1], symbol)
        if len(waypoints) == 1:
            self._place(canvas, waypoints[0][0], waypoints[0][1], symbol)

    def render_map(self, riders: Iterable, orders: Iterable = (),
                   route: Optional[Route] = None) -> str:
        """Render the ASCII map with riders, orders and an optional route.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are
                shown; completed orders are skipped.
            route: Optional Route drawn with '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        canvas = self._blank_canvas()
        if route is not None and route.waypoints:
            self._draw_route(canvas, route.waypoints)
        for order in orders:
            if getattr(order, "status", "") == "completed":
                continue
            self._place(canvas, order.restaurant_x, order.restaurant_y,
                        self.map_symbols["restaurant"])
            self._place(canvas, order.customer_x, order.customer_y,
                        self.map_symbols["customer"])
        for rider in riders:
            self._place(canvas, rider.x, rider.y, self.map_symbols["rider"])

        lines = ["Map (y increases upward, x increases to the right):"]
        for row in reversed(range(CANVAS_SIZE)):
            label = f"{row * RESOLUTION:>4} |"
            lines.append(label + " " + " ".join(canvas[row]))
        lines.append("     " + " ".join("^" if c % 2 == 0 else " "
                                        for c in range(CANVAS_SIZE)))
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=empty *=route")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text reports
    # ------------------------------------------------------------------
    def render_status(self, funds: int, riders: Sequence,
                      issues: Sequence[str] = ()) -> str:
        """Render funds, rider count and per-rider details."""
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        for rider in riders:
            lines.append(
                f"  Rider {rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"status={STATE_NAMES.get(rider.state, rider.state)} "
                f"orders={len(rider.orders)} "
                f"order_ids={[o.id for o in rider.orders]}"
            )
        if issues:
            lines.append("Consistency warnings:")
            lines.extend(f"  - {issue}" for issue in issues)
        return "\n".join(lines)

    def render_orders(self, orders: Sequence) -> str:
        """Render a table of all orders."""
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>8} {'Taken':>6} {'Rider':>6} {'Status':>10}")
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                f"{o.id:>4} {o.start_time:>6} "
                f"{str(o.restaurant_pos):>12} {str(o.customer_pos):>12} "
                f"{o.distance:>8.1f} {taken:>6} {rider:>6} {o.status:>10}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence) -> str:
        """Render every recorded status change for every rider."""
        if not riders:
            return "No riders."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} log:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else entry["order_id"]
                lines.append(
                    f"  t={entry['time']:>5} event={entry['event']:<22} "
                    f"order={order} pos=({entry['x']}, {entry['y']}) "
                    f"state={entry['state']}"
                )
        return "\n".join(lines)

    def render_route(self, route: Route, speed: int) -> str:
        """Render the waypoint list and estimated travel time."""
        lines = [f"Planned route (rider speed {speed} units/tick):"]
        for index, (x, y) in enumerate(route.waypoints):
            lines.append(f"  {index}: ({x}, {y})")
        ticks = math.ceil(route.total_distance / speed) if speed > 0 else 0
        lines.append(f"Total distance: {route.total_distance:.0f} units, "
                     f"estimated time: {ticks} ticks")
        return "\n".join(lines)

    def render_help(self) -> str:
        """Return the command reference."""
        return "\n".join([
            "Commands:",
            "  start [rx ry cx cy]  Place an order (restaurant then customer, 0-800)",
            "  status (s)           Funds, riders and their states",
            "  orders (o)           All orders with timing and rider",
            "  riders (r)           Event log of every rider",
            "  map (m)              ASCII map of riders and orders",
            "  tick [n] (t)         Advance simulated time by n ticks",
            "  save [path] (w)      Save state to JSON",
            "  history (hist)       Show command history",
            "  !! / !n              Repeat last / n-th command",
            "  help (h, ?)          Show this help",
            "  quit (q) / exit (x)  Leave the program",
        ])
