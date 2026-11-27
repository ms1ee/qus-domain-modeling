"""Map, status and log rendering for the command-line interface."""

from typing import List, Optional, Sequence, Tuple

from order_model import STATUS_COMPLETED, Order
from path_planner import GRID_SIZE, PathPlanner, Route
from rider import STATE_NAMES, Rider

Cell = Tuple[int, int]  # (row, col)


class DisplayManager:
    """Renders the 8x8 map, the route graph and status tables as text."""

    SYMBOL_RIDER = "R"
    SYMBOL_RESTAURANT = "S"
    SYMBOL_CUSTOMER = "C"
    SYMBOL_EMPTY = "."
    SYMBOL_STREET = "#"

    def __init__(self, grid_size: int = GRID_SIZE) -> None:
        """Create a display manager.

        Args:
            grid_size: Number of cells along each axis.
        """
        self.grid_size = grid_size

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    @staticmethod
    def cell_of(point: Tuple[int, int]) -> Cell:
        """Return the ``(row, col)`` grid cell for a coordinate point."""
        return (PathPlanner.to_cell_index(point[1]), PathPlanner.to_cell_index(point[0]))

    @staticmethod
    def _line_cells(a: Cell, b: Cell) -> List[Cell]:
        """Return all cells on the axis-aligned line from ``a`` to ``b``."""
        (r1, c1), (r2, c2) = a, b
        if r1 == r2:
            step = 1 if c2 >= c1 else -1
            return [(r1, c) for c in range(c1, c2 + step, step)]
        if c1 == c2:
            step = 1 if r2 >= r1 else -1
            return [(r, c1) for r in range(r1, r2 + step, step)]
        return [a, b]

    @classmethod
    def route_cells(cls, waypoints: Sequence[Tuple[int, int]]) -> List[Cell]:
        """Expand route waypoints into the ordered list of grid cells they cross.

        Args:
            waypoints: Route waypoints in coordinate space.

        Returns:
            Ordered cells without consecutive duplicates.
        """
        cells: List[Cell] = []
        prev: Optional[Cell] = None
        for point in waypoints:
            cur = cls.cell_of(point)
            if prev is None:
                cells.append(cur)
            else:
                cells.extend(cls._line_cells(prev, cur)[1:])
            prev = cur
        return cells

    # ------------------------------------------------------------------
    # Map rendering
    # ------------------------------------------------------------------
    def render_map(self, riders: Sequence[Rider], orders: Sequence[Order],
                   route: Optional[Route] = None) -> str:
        """Render the 8x8 map with riders, restaurants, customers and streets.

        Symbols: ``R`` rider, ``S`` restaurant, ``C`` customer, ``#`` cell
        crossed by the highlighted route, ``.`` empty. Entities take priority
        over street markings.

        Args:
            riders: Riders to display.
            orders: Orders whose active restaurants and customers are shown.
            route: Optional route to highlight.

        Returns:
            Multi-line string.
        """
        n = self.grid_size
        grid = [[self.SYMBOL_EMPTY] * n for _ in range(n)]
        if route is not None:
            for r, c in self.route_cells(route.waypoints):
                grid[r][c] = self.SYMBOL_STREET
        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            r, c = self.cell_of(order.res_center)
            grid[r][c] = self.SYMBOL_RESTAURANT
            r, c = self.cell_of(order.cus_center)
            grid[r][c] = self.SYMBOL_CUSTOMER
        for rider in riders:
            r, c = self.cell_of((rider.x, rider.y))
            grid[r][c] = self.SYMBOL_RIDER

        lines = ["    " + " ".join(str(c) for c in range(n))]
        for r in range(n):
            lines.append(f"{r:>3} " + " ".join(grid[r]))
        lines.append("Legend: R=rider S=restaurant C=customer #=street(route) .=empty")
        return "\n".join(lines)

    def render_route_graph(self, route: Route, restaurant: Tuple[int, int],
                           customer: Tuple[int, int], rider_pos: Tuple[int, int]) -> str:
        """Render a route as a connected line-segment graph on the ASCII map.

        Each grid cell is a node drawn at an even canvas position; route
        segments are drawn with ``-`` (horizontal) and ``|`` (vertical).

        Args:
            route: Planned route.
            restaurant: Restaurant centre point.
            customer: Customer centre point.
            rider_pos: Rider start point (drawn as R).

        Returns:
            Multi-line string.
        """
        n = self.grid_size
        size = 2 * n - 1
        canvas = [[" "] * size for _ in range(size)]
        for r in range(n):
            for c in range(n):
                canvas[2 * r][2 * c] = self.SYMBOL_EMPTY
        cells = self.route_cells(route.waypoints)
        for r, c in cells:
            canvas[2 * r][2 * c] = self.SYMBOL_STREET
        for a, b in zip(cells, cells[1:]):
            mid_r, mid_c = a[0] + b[0], a[1] + b[1]
            canvas[mid_r][mid_c] = "-" if a[0] == b[0] else "|"
        for point, symbol in ((restaurant, self.SYMBOL_RESTAURANT),
                              (customer, self.SYMBOL_CUSTOMER),
                              (rider_pos, self.SYMBOL_RIDER)):
            r, c = self.cell_of(point)
            canvas[2 * r][2 * c] = symbol

        header = "   " + "".join(str(c) if c % 2 == 0 else " " for c in range(size))
        lines = [header]
        for row in range(size):
            label = f"{row // 2:>2} " if row % 2 == 0 else "   "
            lines.append(label + "".join(canvas[row]))
        lines.append("Legend: R=rider start S=restaurant C=customer #=route node "
                     "-/|=route segment")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    @staticmethod
    def state_name(state: int) -> str:
        """Return the human-readable name for a rider state."""
        return STATE_NAMES.get(state, "unknown")

    def render_status(self, funds: int, riders: Sequence[Rider],
                      orders: Sequence[Order]) -> str:
        """Render the system snapshot: funds, riders and active orders.

        Args:
            funds: Current fund balance.
            riders: All riders.
            orders: All orders (completed ones are filtered out).

        Returns:
            Multi-line string.
        """
        lines = [f"System funds: {funds}", f"Riders: {len(riders)}"]
        for rider in riders:
            order_ids = [o.id for o in rider.orders] or "none"
            lines.append(
                f"  Rider {rider.rider_id:<3} pos=({rider.x},{rider.y}) "
                f"state={self.state_name(rider.state)} speed={rider.speed} "
                f"orders={order_ids} special_case={rider.special_case}"
            )
        active = [o for o in orders if o.status != STATUS_COMPLETED]
        lines.append(f"Active orders: {len(active)}")
        for order in active:
            rider_text = order.rider_id if order.rider_id is not None else "-"
            lines.append(
                f"  Order #{order.id} status={order.status} rider={rider_text} "
                f"restaurant={order.res_pos} customer={order.cus_pos}"
            )
        return "\n".join(lines)

    def render_orders(self, orders: Sequence[Order]) -> str:
        """Render a table of all orders.

        Args:
            orders: Orders to display.

        Returns:
            Multi-line string.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} {'Start':>6} {'Restaurant':>12} {'Customer':>12} "
                  f"{'Dist':>6} {'Taken':>6} {'Rider':>6} {'Status':>11}")
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = o.time_taken if o.time_taken is not None else "-"
            rider_text = o.rider_id if o.rider_id is not None else "-"
            lines.append(
                f"{o.id:>4} {o.start_time:>6} {str(o.res_pos):>12} {str(o.cus_pos):>12} "
                f"{o.distance:>6} {str(taken):>6} {str(rider_text):>6} {o.status:>11}"
            )
        return "\n".join(lines)

    def render_rider_logs(self, riders: Sequence[Rider]) -> str:
        """Render the recorded status changes of every rider.

        Args:
            riders: Riders whose logs should be displayed.

        Returns:
            Multi-line string.
        """
        if not riders:
            return "No riders."
        lines: List[str] = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id}:")
            if not rider.log:
                lines.append("  (no records)")
            for entry in rider.log:
                order_text = f" order=#{entry['order_id']}" if entry["order_id"] else ""
                lines.append(
                    f"  [tick {entry['tick']:>5}] {entry['event']:<20}{order_text} "
                    f"pos=({entry['x']},{entry['y']}) "
                    f"state={self.state_name(entry['state'])}"
                )
        return "\n".join(lines)
