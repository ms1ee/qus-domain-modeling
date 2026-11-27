"""Status display and ASCII map visualisation."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from path_planner import GridMap
from rider import STATE_NAMES

Point = Tuple[int, int]


class DisplayManager:
    """Renders the map, status snapshots, order tables and rider logs.

    The ASCII map draws each of the 8x8 grid cell centres as a node. Nodes are
    joined by street segments. Symbols:

        R  rider          S  restaurant      C  customer
        .  empty node     #  street          *  planned route

    Attributes:
        grid_map: The grid coordinate system.
        map_symbols: Mapping of map symbols to their meaning.
    """

    MAP_SYMBOLS = {
        "R": "Rider",
        "S": "Restaurant",
        "C": "Customer",
        ".": "Empty cell",
        "#": "Street",
        "*": "Planned route",
    }

    def __init__(self, grid_map: Optional[GridMap] = None) -> None:
        """Create a display manager.

        Args:
            grid_map: Grid to render. Defaults to the configured grid.
        """
        self.grid_map = grid_map or GridMap.from_config()
        self.map_symbols: Dict[str, str] = dict(self.MAP_SYMBOLS)

    def _canvas_pos(self, pos: Sequence[int]) -> Tuple[int, int]:
        """Convert a map coordinate to a canvas (row, column) position."""
        col = self.grid_map.cell_index(pos[0])
        row = self.grid_map.cell_index(pos[1])
        return 2 * row, 2 * col

    @staticmethod
    def _segment_cells(a: Tuple[int, int], b: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        """Yield canvas cells on an axis-aligned L-shaped path from a to b."""
        r, c = a
        yield r, c
        step_r = 1 if b[0] > r else -1
        while r != b[0]:
            r += step_r
            yield r, c
        step_c = 1 if b[1] > c else -1
        while c != b[1]:
            c += step_c
            yield r, c

    def render_map(
        self,
        riders: Optional[Sequence[Any]] = None,
        orders: Optional[Sequence[Any]] = None,
        route: Optional[Sequence[Point]] = None,
    ) -> str:
        """Render the 8x8 map as ASCII text.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose restaurant ('S') and customer ('C') are shown.
            route: Optional ordered points (start first) drawn as '*' segments.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self.grid_map.size
        width = 2 * size - 1
        canvas: List[List[str]] = []
        for r in range(width):
            row_chars = []
            for c in range(width):
                if r % 2 == 0 and c % 2 == 0:
                    row_chars.append(".")
                elif r % 2 == 0 or c % 2 == 0:
                    row_chars.append("#")
                else:
                    row_chars.append(" ")
            canvas.append(row_chars)

        if route:
            nodes = [self._canvas_pos(point) for point in route]
            for a, b in zip(nodes, nodes[1:]):
                for r, c in self._segment_cells(a, b):
                    canvas[r][c] = "*"
            if nodes:
                canvas[nodes[0][0]][nodes[0][1]] = "*"

        def place(pos: Sequence[int], symbol: str) -> None:
            r, c = self._canvas_pos(pos)
            canvas[r][c] = symbol

        for order in orders or []:
            if order.status == "completed":
                continue
            place(order.restaurant_pos, "S")
            place(order.customer_pos, "C")
        for rider in riders or []:
            place((rider.x, rider.y), "R")

        header = "   " + "".join(
            str(c // 2) if c % 2 == 0 else " " for c in range(width))
        lines = [header]
        for r in range(width):
            label = str(r // 2) if r % 2 == 0 else " "
            lines.append(f"{label:>2} " + "".join(canvas[r]))
        lines.append("Columns: x cell index, rows: y cell index (each cell 100 units).")
        lines.append("Legend: R=Rider S=Restaurant C=Customer .=Cell #=Street *=Route")
        return "\n".join(lines)

    def format_status(self, system: Any) -> str:
        """Build the status snapshot of the whole system.

        Args:
            system: The SystemManager instance.

        Returns:
            Multi-line status text.
        """
        riders = system.riders
        pending = len(_global_list("pending_orders"))
        lines = [
            f"Tick: {system.current_tick}",
            f"System funds: {system.funds}",
            f"Riders: {len(riders)}",
            f"Pending orders: {pending}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: {STATE_NAMES.get(rider.state, rider.state):<11} "
                f"pos=({rider.x},{rider.y}) speed={rider.speed} orders={order_ids}")
        active = [o for o in _global_list("orders") if o.status != "completed"]
        if active:
            lines.append("Active orders:")
            for order in active:
                rider_text = f"#{order.rider_id}" if order.rider_id is not None else "-"
                lines.append(f"  Order #{order.id}: {order.status:<9} rider={rider_text}")
        return "\n".join(lines)

    def format_orders(self, orders: Sequence[Any]) -> str:
        """Build a table with the details of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Formatted table text.
        """
        if not orders:
            return "No orders recorded."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>6} {'Time':>5} {'Rider':>6} {'Status':<10}")
        lines = [header, "-" * len(header)]
        for order in orders:
            rider_text = f"#{order.rider_id}" if order.rider_id is not None else "-"
            time_text = "-" if order.time_taken is None else str(order.time_taken)
            lines.append(
                f"{order.id:>4} {order.start_time:>6} {str(order.restaurant_pos):>12} "
                f"{str(order.customer_pos):>12} {order.distance:>6.2f} {time_text:>5} "
                f"{rider_text:>6} {order.status:<10}")
        return "\n".join(lines)

    def format_rider_logs(self, riders: Sequence[Any]) -> str:
        """Build a chronological log of every rider status change.

        Args:
            riders: Riders whose logs should be merged.

        Returns:
            Multi-line log text.
        """
        entries = []
        for rider in riders:
            for entry in rider.log:
                entries.append((entry.get("time", 0), rider.rider_id, entry))
        if not entries:
            return "No rider events recorded."
        entries.sort(key=lambda item: (item[0], item[1]))
        lines = []
        for time, rider_id, entry in entries:
            order_id = entry.get("order_id")
            order_text = f"#{order_id}" if order_id is not None else "-"
            lines.append(
                f"[t={time:>4}] Rider #{rider_id:<3} {entry.get('event', ''):<22} "
                f"at ({entry.get('x', 0):>3},{entry.get('y', 0):>3}) order {order_text}")
        return "\n".join(lines)


def _global_list(key: str) -> List[Any]:
    """Return a list from the global store, or an empty list."""
    from globalvar import get_value
    return list(get_value(key) or [])
