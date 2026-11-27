"""Status displays and ASCII map visualisation."""

import math

import config
from path_planner import PathPlanner
from rider import STATE_NAMES

SYMBOLS = {
    "empty": " ",
    "intersection": "+",
    "street_h": "-",
    "street_v": "|",
    "restaurant": "R",
    "customer": "C",
    "route": "*",
}


class DisplayManager:
    """Renders status tables, rider logs, routes and the ASCII map."""

    def __init__(self, planner=None):
        """Create a display manager.

        Args:
            planner: Optional PathPlanner used to draw routes.
        """
        self.symbol_map = dict(SYMBOLS)
        self.planner = planner if planner is not None else PathPlanner()

    @staticmethod
    def _cell(x, y):
        """Map a map coordinate to (row, col) on the ASCII canvas.

        Each 100-unit street line is one canvas row/column pair, so the canvas
        has 2*GRID_DIM+1 rows and columns. Row 0 is the top (y = 800).
        """
        col = (int(x) * 2 + config.CELL_SIZE // 2) // config.CELL_SIZE
        row = ((config.MAP_SIZE - int(y)) * 2 + config.CELL_SIZE // 2) // config.CELL_SIZE
        return row, col

    @staticmethod
    def _sample_segment(a, b, step=10):
        """Sample points along an axis-aligned segment every `step` units."""
        (ax, ay), (bx, by) = a, b
        dist = abs(bx - ax) + abs(by - ay)
        count = max(1, dist // step)
        points = []
        for k in range(count + 1):
            t = k / count
            points.append((round(ax + (bx - ax) * t), round(ay + (by - ay) * t)))
        return points

    def render_map(self, riders=(), orders=(), route_points=None):
        """Render the ASCII map.

        Legend: '+' intersection, '-' and '|' streets, 'R' restaurant,
        'C' customer, '*' planned route, digits rider IDs (mod 10).

        Args:
            riders: Riders to draw at their current positions.
            orders: Active orders whose restaurant/customer points are drawn.
            route_points: Optional list of route points to highlight.

        Returns:
            Multi-line string.
        """
        dim = config.GRID_DIM * 2 + 1
        canvas = [[" "] * dim for _ in range(dim)]
        street_chars = (
            self.symbol_map["intersection"],
            self.symbol_map["street_h"],
            self.symbol_map["street_v"],
        )
        for r in range(dim):
            for c in range(dim):
                if r % 2 == 0 and c % 2 == 0:
                    canvas[r][c] = self.symbol_map["intersection"]
                elif r % 2 == 0:
                    canvas[r][c] = self.symbol_map["street_h"]
                elif c % 2 == 0:
                    canvas[r][c] = self.symbol_map["street_v"]
        if route_points:
            for a, b in zip(route_points, route_points[1:]):
                for px, py in self._sample_segment(a, b):
                    row, col = self._cell(px, py)
                    if canvas[row][col] in street_chars:
                        canvas[row][col] = self.symbol_map["route"]
        for order in orders:
            if order.status == "completed":
                continue
            row, col = self._cell(*order.res_pos)
            canvas[row][col] = self.symbol_map["restaurant"]
            row, col = self._cell(*order.cus_pos)
            canvas[row][col] = self.symbol_map["customer"]
        for rider in riders:
            row, col = self._cell(rider.x, rider.y)
            canvas[row][col] = str(rider.rider_id % 10)

        lines = []
        for r in range(dim):
            if r % 2 == 0:
                y_value = config.MAP_SIZE - (r // 2) * config.CELL_SIZE
                label = f"{y_value:>4} "
            else:
                label = "     "
            lines.append(label + "".join(canvas[r]))
        lines.append("")
        lines.append("Legend: + intersection, - |streets, R restaurant, "
                     "C customer, * route, 0-9 rider ID")
        lines.append("Grid lines every 100 units (x and y: 0 to 800).")
        return "\n".join(lines)

    def render_route(self, rider, order):
        """Render the route map for a rider including speed and time estimate.

        Args:
            rider: Assigned rider.
            order: Newly assigned order.

        Returns:
            Multi-line string describing the route and drawing it on the map.
        """
        stops = []
        for queued in rider.orders:
            if not queued.picked_up:
                stops.append(queued.res_pos)
            stops.append(queued.cus_pos)
        if order not in rider.orders:
            stops.extend([order.res_pos, order.cus_pos])
        points = self.planner.plan_route(rider.position, stops)
        length = self.planner.route_length(points)
        speed = max(1, rider.speed)
        eta = math.ceil(length / speed) if length else 0
        header = (
            f"Route for rider {rider.rider_id}: speed={rider.speed} units/tick, "
            f"path length={length} units, estimated time={eta} tick(s)"
        )
        return header + "\n" + self.render_map(
            riders=[rider], orders=[order], route_points=points
        )

    def render_status(self, funds, tick, riders):
        """Render the system snapshot: funds, tick and every rider.

        Args:
            funds: Current fund balance.
            tick: Current simulated tick.
            riders: Iterable of riders.

        Returns:
            Multi-line string.
        """
        riders = list(riders)
        lines = [
            f"Tick: {tick}",
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.order_id for o in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id}: position=({rider.x},{rider.y}) "
                f"status={STATE_NAMES.get(rider.state, 'unknown')} "
                f"speed={rider.speed} orders={len(order_ids)} {order_ids} "
                f"special_case={rider.special_case}"
            )
        if not riders:
            lines.append("  No riders recruited yet.")
        return "\n".join(lines)

    def render_orders(self, orders):
        """Render a table of orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            Multi-line string.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        header = (
            f"{'ID':>4} | {'Start':>5} | {'Restaurant':>12} | {'Customer':>12} | "
            f"{'Dist':>5} | {'Time':>5} | {'Rider':>5} | {'Status':<12} | {'Eff':>6}"
        )
        lines = [header, "-" * len(header)]
        for o in orders:
            rider = "-" if o.rider_id is None else str(o.rider_id)
            time_taken = "-" if o.time_taken is None else str(o.time_taken)
            lines.append(
                f"{o.order_id:>4} | {o.start_time:>5} | {str(o.res_pos):>12} | "
                f"{str(o.cus_pos):>12} | {o.distance:>5} | {time_taken:>5} | "
                f"{rider:>5} | {o.status:<12} | {o.efficiency:>6.2f}"
            )
        return "\n".join(lines)

    def render_riders(self, riders):
        """Render the status-change log of every given rider.

        Args:
            riders: Iterable of riders.

        Returns:
            Multi-line string.
        """
        lines = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} log:")
            if not rider.log:
                lines.append("  (no events)")
            for entry in rider.log:
                order = "-" if entry["order_id"] is None else entry["order_id"]
                lines.append(
                    f"  [tick {entry['tick']}] {entry['event']:<22} "
                    f"order={order} pos=({entry['x']},{entry['y']}) "
                    f"state={STATE_NAMES.get(entry['state'], 'unknown')}"
                )
        return "\n".join(lines) if lines else "No riders recruited yet."
