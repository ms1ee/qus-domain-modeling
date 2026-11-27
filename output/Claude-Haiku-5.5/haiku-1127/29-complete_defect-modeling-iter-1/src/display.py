"""Status text and ASCII map rendering for the dispatch simulator."""

from typing import Iterable, List, Optional, Sequence

from path_planner import CELL_HALF, CELL_SIZE, GRID_DIM, Point
from rider import STATE_NAMES, Rider


def _round_half_up(value: float) -> int:
    """Round to the nearest integer, halves rounding up."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


class DisplayManager:
    """Renders the 8x8 map and textual status reports.

    Map layout: every grid cell center is a node drawn at an even
    row/column of a 15x15 character canvas, and streets connecting adjacent
    nodes are drawn at the odd positions in between.

    Symbols:
        R rider, S restaurant, C customer, . empty node, # street,
        * route taken by a rider.
    """

    def __init__(self) -> None:
        """Create the display manager with its symbol legend."""
        self.map_symbols: str = "R=rider S=restaurant C=customer .=empty #=street *=route"
        self._size: int = 2 * GRID_DIM - 1

    def _to_canvas(self, point: Point):
        """Convert a map coordinate into canvas (row, column) indexes."""
        x, y = point
        half = CELL_SIZE // 2
        col = _round_half_up((x - CELL_HALF) / half)
        node_row = _round_half_up((y - CELL_HALF) / half)
        col = min(max(col, 0), self._size - 1)
        row = min(max(self._size - 1 - node_row, 0), self._size - 1)
        return row, col

    def _put(self, canvas: List[List[str]], point: Point, symbol: str) -> None:
        """Place a symbol on the canvas at a map coordinate."""
        row, col = self._to_canvas(point)
        canvas[row][col] = symbol

    def render_map(
        self,
        riders: Optional[Iterable[Rider]] = None,
        orders: Optional[Iterable] = None,
        routes: Optional[Iterable[Sequence[Point]]] = None,
    ) -> str:
        """Render the ASCII map with riders, orders and routes.

        Args:
            riders: Riders whose positions are marked with 'R'.
            orders: Orders whose restaurants ('S') and customers ('C') are marked.
            routes: Sequences of visited points drawn with '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        size = self._size
        canvas: List[List[str]] = []
        for r in range(size):
            row_cells = []
            for c in range(size):
                if r % 2 == 0 and c % 2 == 0:
                    row_cells.append(".")
                elif r % 2 == 1 and c % 2 == 1:
                    row_cells.append(" ")
                else:
                    row_cells.append("#")
            canvas.append(row_cells)

        for route in routes or []:
            for point in route:
                row, col = self._to_canvas(point)
                if canvas[row][col] in ".#":
                    canvas[row][col] = "*"

        for order in orders or []:
            self._put(canvas, order.res_pos, "S")
            self._put(canvas, order.cus_pos, "C")

        for rider in riders or []:
            self._put(canvas, rider.position, "R")

        header = [" "] * (2 + 2 * size)
        for i in range(GRID_DIM):
            header[2 + 4 * i] = str(i)
        lines = ["".join(header).rstrip()]
        for r, row_cells in enumerate(canvas):
            label = str(GRID_DIM - 1 - r // 2) if r % 2 == 0 else " "
            lines.append(f"{label} " + " ".join(row_cells))
        lines.append("")
        lines.append("Legend: " + self.map_symbols)
        lines.append("Columns: x grid index (0-7), rows: y grid index (0-7, top = 7).")
        return "\n".join(lines)

    def status_text(self, funds: int, simulated_time: int, riders: Sequence[Rider], active_orders: Sequence) -> str:
        """Build the snapshot report shown by the ``status`` command.

        Args:
            funds: Current system funds.
            simulated_time: Current tick.
            riders: All riders.
            active_orders: Orders not yet completed.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"Simulated time : {simulated_time} ticks",
            f"System funds   : {funds}",
            f"Riders         : {len(riders)}",
            f"Active orders  : {len(active_orders)}",
        ]
        for rider in riders:
            order_ids = [order.id for order in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id:<3} {STATE_NAMES[rider.state]:<11} "
                f"pos=({rider.x},{rider.y}) orders={order_ids}"
            )
        return "\n".join(lines)

    def riders_text(self, riders: Sequence[Rider]) -> str:
        """Build the detailed rider report with every logged status change.

        Args:
            riders: Riders to report on.

        Returns:
            Multi-line text.
        """
        if not riders:
            return "No riders recruited yet."
        lines: List[str] = []
        for rider in riders:
            lines.append(
                f"Rider #{rider.rider_id} | state={STATE_NAMES[rider.state]} | "
                f"pos=({rider.x},{rider.y}) | speed={rider.speed} | "
                f"special_case={rider.special_case} | distance={rider.distance_traveled}"
            )
            if not rider.log:
                lines.append("    (no events)")
            for entry in rider.log:
                order_text = entry["order_id"] if entry["order_id"] is not None else "-"
                lines.append(
                    f"    t={entry['time']:<6} {entry['event']:<22} order={order_text:<5} "
                    f"state={STATE_NAMES.get(entry['state'], '?'):<11} "
                    f"pos=({entry['x']},{entry['y']})"
                )
        return "\n".join(lines)

    def orders_text(self, orders: Sequence) -> str:
        """Build the order table shown by the ``orders`` command.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line table text.
        """
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':<4}{'Start':<7}{'Restaurant':<13}{'Customer':<13}"
            f"{'Distance':<10}{'Time':<7}{'Rider':<7}{'Status':<12}{'Eff.':<6}"
        )
        lines = [header, "-" * len(header)]
        for order in orders:
            rider_text = f"#{order.rider_id}" if order.rider_id is not None else "-"
            time_text = str(order.time_taken) if order.time_taken is not None else "-"
            eff_text = f"{order.efficiency:.2f}" if order.efficiency is not None else "-"
            lines.append(
                f"{order.id:<4}{order.start_time:<7}"
                f"{str(order.res_pos):<13}{str(order.cus_pos):<13}"
                f"{order.distance:<10.0f}{time_text:<7}{rider_text:<7}"
                f"{order.status:<12}{eff_text:<6}"
            )
        return "\n".join(lines)
