"""Status display and ASCII map visualization."""

from globalvar import get_value
from order_model import STATUS_COMPLETED
from path_planner import GRID_DIM, cell_index
from rider import STATE_NAMES

SYMBOL_RIDER = "R"
SYMBOL_RESTAURANT = "S"
SYMBOL_CUSTOMER = "C"
SYMBOL_EMPTY = "."
SYMBOL_STREET = "#"


class DisplayManager:
    """Produces text output for status, orders, rider logs and the map."""

    def render_map(self, riders, orders, route=None) -> str:
        """Render the 8x8 ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' route/street,
        '.' empty. Priority when cells overlap: R > S > C > # > '.'.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects (completed orders are hidden).
            route: Optional list of (x, y) waypoints drawn as a line.

        Returns:
            Multi-line string with the map and a legend.
        """
        grid = [[SYMBOL_EMPTY] * GRID_DIM for _ in range(GRID_DIM)]

        if route:
            for (ax, ay), (bx, by) in zip(route, route[1:]):
                steps = max(abs(bx - ax), abs(by - ay))
                if steps == 0:
                    self._set(grid, ax, ay, SYMBOL_STREET, only_empty=True)
                    continue
                for i in range(steps + 1):
                    px = ax + (bx - ax) * i // steps
                    py = ay + (by - ay) * i // steps
                    self._set(grid, px, py, SYMBOL_STREET, only_empty=True)

        for order in orders:
            if order.status == STATUS_COMPLETED:
                continue
            self._set(grid, order.cus_pos[0], order.cus_pos[1], SYMBOL_CUSTOMER)
            self._set(grid, order.res_pos[0], order.res_pos[1], SYMBOL_RESTAURANT)

        for rider in riders:
            self._set(grid, rider.x, rider.y, SYMBOL_RIDER)

        lines = [" " * 11 + " ".join(str(c) for c in range(GRID_DIM))]
        for row in reversed(range(GRID_DIM)):
            start = row * 100
            label = f"y{start:03d}-{start + 100:03d} |"
            lines.append(label + " " + " ".join(grid[row]))
        lines.append("x cells: 0..7 (each cell 100 units)")
        lines.append(
            "Legend: R=Rider S=Restaurant C=Customer #=Street/Route .=Empty"
        )
        return "\n".join(lines)

    @staticmethod
    def _set(grid, x, y, symbol, only_empty=False) -> None:
        """Place a symbol in the grid cell containing (x, y)."""
        col = cell_index(x)
        row = cell_index(y)
        if only_empty and grid[row][col] != SYMBOL_EMPTY:
            return
        grid[row][col] = symbol

    @staticmethod
    def format_status(system) -> str:
        """Return a snapshot of funds, riders and their orders.

        Args:
            system: SystemManager instance.

        Returns:
            Multi-line status text.
        """
        lines = [
            f"Tick: {system.tick_count}",
            f"System funds: {system.funds}",
            f"Riders: {len(system.riders)}",
        ]
        for rider in system.riders:
            order_text = ", ".join(
                f"#{o.id}({o.status})" for o in rider.orders
            ) or "none"
            lines.append(
                f"  Rider #{rider.rider_id}: position=({rider.x}, {rider.y}) "
                f"state={STATE_NAMES.get(rider.state, rider.state)} "
                f"orders={len(rider.orders)} [{order_text}]"
            )
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders) -> str:
        """Return a table of all orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line table text.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = [
            "ID   Start  Restaurant   Customer     Distance  Taken  Rider  Status"
        ]
        for o in orders:
            taken = o.time_taken if o.time_taken is not None else "-"
            rider = f"#{o.rider_id}" if o.rider_id is not None else "-"
            lines.append(
                f"{o.id:<4} {o.start_tick:<6} {str(o.res_pos):<12} "
                f"{str(o.cus_pos):<12} {o.distance:<9} {str(taken):<6} "
                f"{rider:<6} {o.status}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_rider_log(riders) -> str:
        """Return every recorded status change for all riders.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            Multi-line text, grouped by rider.
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider #{rider.rider_id}:")
            for entry in rider.log:
                order_text = (
                    f"order #{entry['order_id']}" if entry["order_id"] is not None else "-"
                )
                lines.append(
                    f"  t={entry['tick']:<4} {entry['event']:<22} {order_text:<12} "
                    f"pos=({entry['x']}, {entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], entry['state'])}"
                )
        return "\n".join(lines)

    @staticmethod
    def format_route(route) -> str:
        """Return a readable representation of a waypoint list."""
        if not route:
            return "-"
        return " -> ".join(f"({x}, {y})" for x, y in route)
