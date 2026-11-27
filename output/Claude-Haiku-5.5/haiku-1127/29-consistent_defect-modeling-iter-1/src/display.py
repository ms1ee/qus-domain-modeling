"""Status displays and ASCII map visualisation."""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from order_model import Order
from rider import STATE_NAMES, Rider

Point = Tuple[int, int]

MAP_CELLS = 16
MAP_STEP = 50  # each character represents 50 x 50 units (800 / 16)

SYMBOLS: Dict[str, str] = {
    "rider": "R",
    "restaurant": "S",
    "customer": "C",
    "empty": ".",
    "street": "#",
    "route": "*",
}

EVENT_TEXT: Dict[str, str] = {
    "spawn": "spawned",
    "accepted_order": "accepted order",
    "arrived_at_merchant": "arrived at restaurant",
    "delivered_to_customer": "delivered to customer",
}


class DisplayManager:
    """Renders the system status, order table, rider logs and ASCII map.

    Attributes:
        map_size: Map side length in units.
        symbol_map: Symbols used on the ASCII map.
    """

    def __init__(self, map_size: int = 800) -> None:
        self.map_size = map_size
        self.symbol_map: Dict[str, str] = dict(SYMBOLS)

    def render_status(self, funds: int, riders: Sequence[Rider]) -> str:
        """Return a snapshot of funds and every rider's state and orders."""
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("  (no riders on duty)")
        for rider in riders:
            state = STATE_NAMES.get(rider.state, "unknown")
            active = [o.id for o in rider.active_orders()]
            done = [o.id for o in rider.orders if o.status == "completed"]
            lines.append(
                f"  R{rider.rider_id}: position=({rider.x},{rider.y}) "
                f"status={state} speed={rider.speed} "
                f"active_orders={active or '-'} completed={done or '-'}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Iterable[Order]) -> str:
        """Return a table of all orders with timing and assignment data."""
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = [
            "ID  start  restaurant  customer    distance  time  rider  status"
        ]
        for o in orders:
            time_taken = "-" if o.time_taken is None else str(o.time_taken)
            rider = "-" if o.rider_id is None else f"R{o.rider_id}"
            lines.append(
                f"{o.id:<3} {o.start_time:<6} "
                f"{str(o.res_pos):<11} {str(o.cus_pos):<11} "
                f"{o.distance:<9.1f} {time_taken:<5} {rider:<6} {o.status}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Rider]) -> str:
        """Return every recorded status change for all riders."""
        if not riders:
            return "No riders on duty."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"R{rider.rider_id}:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else f"#{entry['order_id']}"
                text = EVENT_TEXT.get(entry["event"], entry["event"])
                lines.append(
                    f"  t={entry['time']:<5} {text:<24} order={order:<5} "
                    f"pos=({entry['x']},{entry['y']}) state={entry['state']}"
                )
        return "\n".join(lines)

    def render_map(
        self,
        riders: Sequence[Rider],
        orders: Iterable[Order],
        routes: Optional[Sequence[Sequence[Point]]] = None,
    ) -> str:
        """Render the 16x16 ASCII map.

        Layers (lowest to highest priority): street, route, customer,
        restaurant, rider. Each character covers 50x50 units.

        Args:
            riders: Riders to mark with 'R'.
            orders: Orders whose pending/active restaurant and customer
                locations are marked with 'S' and 'C'.
            routes: Optional polylines (lists of points) drawn with '*'.

        Returns:
            Multi-line string containing the map and a legend.
        """
        s = self.symbol_map
        grid = [[s["empty"]] * MAP_CELLS for _ in range(MAP_CELLS)]
        for row in range(MAP_CELLS):
            for col in range(MAP_CELLS):
                if row % 2 == 0 or col % 2 == 0:
                    grid[row][col] = s["street"]

        for polyline in routes or []:
            for a, b in zip(polyline, polyline[1:]):
                for px, py in self._sample_segment(a, b):
                    self._mark(grid, px, py, s["route"])

        for order in orders:
            if order.status == "completed":
                continue
            self._mark(grid, order.res_pos[0], order.res_pos[1], s["restaurant"])
            self._mark(grid, order.cus_pos[0], order.cus_pos[1], s["customer"])

        for rider in riders:
            self._mark(grid, rider.x, rider.y, s["rider"])

        lines = [f"{row * MAP_STEP:>4} " + " ".join(cells) for row, cells in enumerate(grid)]
        header = "     " + " ".join(str((c * MAP_STEP) // 100 % 10) for c in range(MAP_CELLS))
        legend = (
            "Legend: R=rider S=restaurant C=customer #=street "
            ". =empty *=route | 1 char = 50 units (y down, x right)"
        )
        return "\n".join([header] + lines + [legend])

    @staticmethod
    def _mark(grid: List[List[str]], x: int, y: int, symbol: str) -> None:
        """Place a symbol on the grid for map coordinates (x, y)."""
        col = min(MAP_CELLS - 1, max(0, int(x) // MAP_STEP))
        row = min(MAP_CELLS - 1, max(0, int(y) // MAP_STEP))
        grid[row][col] = symbol

    @staticmethod
    def _sample_segment(a: Point, b: Point) -> List[Point]:
        """Sample points along an axis-aligned segment for route drawing."""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = abs(dx) + abs(dy)
        steps = max(1, length // 25)
        points: List[Point] = []
        for k in range(steps + 1):
            points.append((a[0] + dx * k // steps, a[1] + dy * k // steps))
        return points
