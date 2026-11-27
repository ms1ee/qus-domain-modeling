"""Status displays and ASCII map visualisation."""

import globalvar
import grid
from rider import STATE_NAMES

MAP_CELLS = grid.GRID_DIM            # 8
MAP_NODES = grid.LATTICE_DIM         # 9


class DisplayManager:
    """Render the map, system status, order list and rider logs as text."""

    @staticmethod
    def _cell(point):
        """Return the (row, col) character position for a map point.

        Intersections sit at even row/column indices. Odd indices hold the
        street segments between intersections. Row 0 is the top (y = 800).
        """
        gx = min(max(int(round(point[0] / grid.CELL_SIZE)), 0), MAP_CELLS)
        gy = min(max(int(round(point[1] / grid.CELL_SIZE)), 0), MAP_CELLS)
        return 2 * (MAP_CELLS - gy), 2 * gx

    @classmethod
    def render_map(cls, route=None, riders=None):
        """Render the 8x8 grid as an ASCII map.

        Symbols: '.' intersection, '-' and '|' streets, 'M' restaurant,
        'C' customer, 'R' rider, '*' planned route.

        Args:
            route: Optional list of corner points to highlight.
            riders: Optional list of riders; defaults to the global list.

        Returns:
            Multi-line string containing the map and legend.
        """
        if riders is None:
            riders = globalvar.get_value("riders", [])
        size = 2 * MAP_CELLS + 1
        canvas = [[" "] * size for _ in range(size)]

        for gx in range(MAP_NODES):
            for gy in range(MAP_NODES):
                r, c = cls._cell((gx * grid.CELL_SIZE, gy * grid.CELL_SIZE))
                canvas[r][c] = "."
                if gx < MAP_CELLS:
                    canvas[r][c + 1] = "-"
                if gy < MAP_CELLS:
                    canvas[r - 1][c] = "|"

        if route:
            for a, b in zip(route, route[1:]):
                r, c = cls._cell(a)
                rb, cb = cls._cell(b)
                canvas[r][c] = "*"
                while (r, c) != (rb, cb):
                    if r != rb:
                        r += 1 if rb > r else -1
                    if c != cb:
                        c += 1 if cb > c else -1
                    canvas[r][c] = "*"

        for rider in riders:
            for order in rider.orders:
                r, c = cls._cell(order.res_pos)
                canvas[r][c] = "M"
                r, c = cls._cell(order.cus_pos)
                canvas[r][c] = "C"
        for rider in riders:
            r, c = cls._cell(rider.position)
            canvas[r][c] = "R"

        lines = []
        for index, row in enumerate(canvas):
            if index % 2 == 0:
                y_value = grid.MAP_SIZE - (index // 2) * grid.CELL_SIZE
                label = f"{y_value:>4} "
            else:
                label = "     "
            lines.append(label + "".join(row))
        lines.append("     x: 0 (left) .. 800 (right); y: 0 (bottom) .. 800 (top)")
        lines.append("     Legend: R rider, M restaurant, C customer, "
                     ". intersection, - | street, * planned route")
        return "\n".join(lines)

    @staticmethod
    def render_status(funds, riders, time_now, issues=None):
        """Render a snapshot of system funds and every rider.

        Args:
            funds: Current fund balance.
            riders: List of Rider objects.
            time_now: Current simulated time.
            issues: Optional list of consistency problems.

        Returns:
            Multi-line status string.
        """
        lines = [
            f"Simulated time: {time_now} tick(s)",
            f"System funds: {funds}",
            f"Riders: {len(riders)}",
        ]
        for rider in riders:
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider #{rider.rider_id}: position ({rider.x}, {rider.y}), "
                f"status {STATE_NAMES.get(rider.state, 'unknown')}, "
                f"speed {rider.speed}, orders {len(order_ids)} {order_ids}"
            )
        if issues:
            lines.append("Consistency issues:")
            lines.extend(f"  ! {issue}" for issue in issues)
        return "\n".join(lines)

    @staticmethod
    def render_orders(orders, time_now):
        """Render a table of all orders.

        Args:
            orders: List of Order objects.
            time_now: Current simulated time (for unfinished orders).

        Returns:
            Multi-line table string.
        """
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>4} | {'Start':>5} | {'Restaurant':<12} | "
                  f"{'Customer':<12} | {'Dist':>5} | {'Taken':>10} | "
                  f"{'Rider':>5} | Status")
        lines = [header, "-" * len(header)]
        for order in orders:
            if order.time_taken() is not None:
                taken = f"{order.time_taken()} tick(s)"
            else:
                taken = f"({time_now - order.created_time} so far)"
            rider = f"#{order.rider_id}" if order.rider_id is not None else "-"
            lines.append(
                f"{order.id:>4} | {order.created_time:>5} | "
                f"{str(order.res_pos):<12} | {str(order.cus_pos):<12} | "
                f"{order.distance:>5} | {taken:>10} | {rider:>5} | {order.status}"
            )
        return "\n".join(lines)

    @staticmethod
    def render_rider_log(riders):
        """Render every status-change entry of all riders in time order.

        Args:
            riders: List of Rider objects.

        Returns:
            Multi-line log string.
        """
        entries = []
        for rider in riders:
            entries.extend(rider.log)
        if not entries:
            return "No rider events recorded."
        entries.sort(key=lambda e: (e["time"], e["rider_id"]))
        lines = []
        for entry in entries:
            order = (f"order #{entry['order_id']}"
                     if entry["order_id"] is not None else "no order")
            lines.append(
                f"t={entry['time']:>4} | Rider #{entry['rider_id']:<3} | "
                f"{entry['event']:<20} | {order:<10} | "
                f"at ({entry['x']}, {entry['y']}) | "
                f"{STATE_NAMES.get(entry['state'], 'unknown')}"
            )
        return "\n".join(lines)
