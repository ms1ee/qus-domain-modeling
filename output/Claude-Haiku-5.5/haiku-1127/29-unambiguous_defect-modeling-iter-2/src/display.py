"""Status tables and ASCII map rendering."""

import logging
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from globalvar import get_value
from grid_map import GRID_DIMENSION, MAP_SIZE
from rider import Rider

logger = logging.getLogger(__name__)

HALF = 50  # one canvas character represents 50 units


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


def _axis_path(a: Sequence[int], b: Sequence[int]):
    """Yield every unit point along an axis-aligned segment from a to b.

    Args:
        a (tuple[int, int]): Start point.
        b (tuple[int, int]): End point.

    Yields:
        tuple[int, int]: Points on the segment.
    """
    x0, y0 = a
    x1, y1 = b
    sx = _sign(x1 - x0)
    sy = _sign(y1 - y0)
    for i in range(abs(x1 - x0) + 1):
        yield x0 + sx * i, y0
    for j in range(1, abs(y1 - y0) + 1):
        yield x1, y0 + sy * j


class DisplayManager:
    """Formats status information and renders the ASCII map.

    The 800x800 map is drawn on a 17x17 character canvas: intersections are
    '+', horizontal streets '-', vertical streets '|', and location cells
    (cell centres) are '.' unless occupied by a marker.

    Attributes:
        symbolMap (dict[str, str]): Symbol for each map element.
    """

    CANVAS_SIZE = 2 * GRID_DIMENSION + 1
    ROUTE_REPLACEABLE = ("-", "|", "+", ".", " ")

    def __init__(self):
        """Create the display with the default symbol mapping."""
        self.symbolMap = {
            "empty": ".",
            "street_h": "-",
            "street_v": "|",
            "intersection": "+",
            "restaurant": "M",
            "customer": "C",
            "rider": "R",
            "route": "*",
            "space": " ",
        }

    def _blank_canvas(self) -> List[List[str]]:
        """Build the base canvas containing streets and empty cells.

        Returns:
            list[list[str]]: Canvas rows of symbols.
        """
        size = self.CANVAS_SIZE
        canvas = []
        for row in range(size):
            line = []
            for col in range(size):
                if row % 2 == 0 and col % 2 == 0:
                    line.append(self.symbolMap["intersection"])
                elif row % 2 == 0:
                    line.append(self.symbolMap["street_h"])
                elif col % 2 == 0:
                    line.append(self.symbolMap["street_v"])
                else:
                    line.append(self.symbolMap["empty"])
            canvas.append(line)
        return canvas

    @staticmethod
    def _to_canvas(x: int, y: int) -> Tuple[int, int]:
        """Convert a map coordinate to a canvas (row, col) index.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.

        Returns:
            tuple[int, int]: Row and column indices.
        """
        col = min(max(int(x), 0), MAP_SIZE) // HALF
        row = min(max(int(y), 0), MAP_SIZE) // HALF
        return row, col

    def _put(self, canvas, x: int, y: int, symbol: str) -> None:
        """Place a symbol at a map coordinate.

        Args:
            canvas (list[list[str]]): Canvas to modify.
            x (int): X coordinate.
            y (int): Y coordinate.
            symbol (str): Symbol to draw.
        """
        row, col = self._to_canvas(x, y)
        canvas[row][col] = symbol

    def _draw_route(self, canvas, route: Sequence[Tuple[int, int]]) -> None:
        """Draw a connected route line with the route symbol.

        Markers such as restaurants, customers, and riders are not
        overwritten.

        Args:
            canvas (list[list[str]]): Canvas to modify.
            route (sequence[tuple[int, int]]): Ordered route points.
        """
        route_symbol = self.symbolMap["route"]
        replaceable = set(self.ROUTE_REPLACEABLE)
        for a, b in zip(route, route[1:]):
            for x, y in _axis_path(a, b):
                row, col = self._to_canvas(x, y)
                if canvas[row][col] in replaceable:
                    canvas[row][col] = route_symbol

    def render_map(self, riders: Iterable[Rider] = (),
                   orders: Iterable[Any] = (),
                   route: Optional[Sequence[Tuple[int, int]]] = None) -> str:
        """Render the ASCII map with riders, orders, and an optional route.

        Args:
            riders (iterable[Rider]): Riders to mark with 'R'.
            orders (iterable[Order]): Active orders; restaurants are marked
                'M' and customers 'C'.
            route (sequence[tuple[int, int]] | None): Route to draw as a
                connected line of '*'. The first point is the start.

        Returns:
            str: Multi-line map text including a legend.
        """
        canvas = self._blank_canvas()
        if route:
            self._draw_route(canvas, route)
        for order in orders:
            if getattr(order, "status", "") == "completed":
                continue
            self._put(canvas, order.res_pos[0], order.res_pos[1],
                      self.symbolMap["restaurant"])
            self._put(canvas, order.cus_pos[0], order.cus_pos[1],
                      self.symbolMap["customer"])
        for rider in riders:
            self._put(canvas, rider.x, rider.y, self.symbolMap["rider"])

        lines = ["     x: 0 (left) -> 800 (right)"]
        for row_index, row in enumerate(canvas):
            if row_index % 2 == 1:
                label = f"{(row_index // 2) * 100 + 50:>4} "
            else:
                label = "     "
            lines.append(label + " ".join(row))
        lines.append("y: 0 (top) -> 800 (bottom); rows labelled at cell centres")
        lines.append("Legend: + intersection  - | street  . location  "
                     "M restaurant  C customer  R rider  * route")
        return "\n".join(lines)

    def format_status(self, system) -> str:
        """Build the system status report.

        Args:
            system (SystemManager): The running system.

        Returns:
            str: Funds, tick, rider table, and consistency information.
        """
        riders = system.riders
        active = [o for o in get_value("orders", []) if o.is_active]
        issues = system.check_consistency()
        lines = [
            "=== System Status ===",
            f"Funds: {system.funds}",
            f"Simulated tick: {system.currentTick}",
            f"Riders: {len(riders)} (recruitment cost {system.recruitmentCost})",
            f"Active orders: {len(active)}",
            f"Consistency: {'OK' if not issues else '; '.join(issues)}",
            "",
            f"{'ID':<6}{'Position':<16}{'State':<14}{'Speed':<7}Orders",
        ]
        for rider in riders:
            state = Rider.STATE_NAMES.get(rider.state, "unknown")
            order_ids = ", ".join(str(o.id) for o in rider.orders) or "-"
            pos = f"({rider.x}, {rider.y})"
            lines.append(f"{'R' + str(rider.rider_id):<6}{pos:<16}"
                         f"{state:<14}{rider.speed:<7}{order_ids}")
        if not riders:
            lines.append("No riders on duty.")
        return "\n".join(lines)

    def format_orders(self, orders: Iterable[Any]) -> str:
        """Build the order detail table.

        Args:
            orders (iterable[Order]): Orders to display.

        Returns:
            str: Formatted table text.
        """
        header = (f"{'ID':<5}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
                  f"{'Distance':<10}{'Time':<7}{'Rider':<7}Status")
        lines = ["=== Orders ===", header]
        count = 0
        for order in orders:
            count += 1
            time_text = (str(order.time_taken)
                         if order.time_taken is not None else "-")
            rider_text = (f"R{order.rider_id}"
                          if order.rider_id is not None else "-")
            res = f"({order.restaurant_x},{order.restaurant_y})"
            cus = f"({order.customer_x},{order.customer_y})"
            lines.append(f"{order.id:<5}{order.start_time:<7}{res:<13}"
                         f"{cus:<13}{order.distance:<10.1f}{time_text:<7}"
                         f"{rider_text:<7}{order.status}")
        if count == 0:
            lines.append("No orders yet.")
        return "\n".join(lines)

    def format_rider_logs(self, riders: Iterable[Rider]) -> str:
        """Build the chronological rider event log.

        Args:
            riders (iterable[Rider]): Riders whose logs are shown.

        Returns:
            str: One line per status change, ordered by tick.
        """
        entries = []
        for rider in riders:
            entries.extend(rider.log)
        entries.sort(key=lambda e: (e["tick"], e["rider_id"]))
        lines = ["=== Rider Event Log ==="]
        for entry in entries:
            order_text = (f"order {entry['order_id']}"
                          if entry["order_id"] is not None else "-")
            state = Rider.STATE_NAMES.get(entry["state"], "unknown")
            lines.append(f"[tick {entry['tick']:>4}] R{entry['rider_id']:<3} "
                         f"{entry['event']:<22} {order_text:<12} "
                         f"at ({entry['x']}, {entry['y']}) state={state}")
        if not entries:
            lines.append("No rider events yet.")
        return "\n".join(lines)
