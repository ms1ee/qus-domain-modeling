"""Status displays, rider/order reports and ASCII map rendering."""

from path_planner import MAP_SIZE, CELL_SIZE, PathPlanner
from rider import STATE_NAMES

STEP = 50                       # map character resolution (units per char)
MAP_CHARS = MAP_SIZE // STEP + 1  # 17 characters per axis (9x9 intersections)


def _idx(value):
    """Convert a coordinate to a map character index.

    Args:
        value: Coordinate in units.

    Returns:
        int: Index clamped to the map range.
    """
    return min(MAP_CHARS - 1, max(0, round(value / STEP)))


class DisplayManager:
    """Builds text output for status, orders, rider logs and the map."""

    def render_status(self, system, riders):
        """Snapshot of funds, riders, their states and order lists.

        Args:
            system: SystemManager instance.
            riders: Iterable of Rider objects.

        Returns:
            str: Multi-line report.
        """
        riders = list(riders)
        lines = [
            "=== System Status ===",
            "Tick: %d" % system.tick_count,
            "System funds: %d" % system.funds,
            "Riders: %d" % len(riders),
        ]
        for rider in riders:
            col, row = PathPlanner.grid_cell(rider.x, rider.y)
            order_text = ", ".join(
                "#%d:%s" % (o.id, o.status) for o in rider.orders
            ) or "none"
            lines.append(
                "  Rider %d | pos=(%d,%d) cell=(%d,%d) | state=%s | "
                "active=%d | orders: %s"
                % (rider.rider_id, rider.x, rider.y, col, row,
                   STATE_NAMES.get(rider.state, "unknown"),
                   rider.active_order_count(), order_text)
            )
        return "\n".join(lines)

    def render_orders(self, orders):
        """Detailed table of all orders.

        Args:
            orders: Iterable of Order objects.

        Returns:
            str: Multi-line report.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ==="]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            eff = "-" if o.efficiency is None else str(o.efficiency)
            rider = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(
                "  #%d start=t%d restaurant=%s customer=%s distance=%d "
                "time_taken=%s efficiency=%s rider=%s status=%s"
                % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                   taken, eff, rider, o.status)
            )
        return "\n".join(lines)

    def render_rider_log(self, riders):
        """Every recorded status change for every rider.

        Args:
            riders: Iterable of Rider objects.

        Returns:
            str: Multi-line report.
        """
        lines = ["=== Rider Status Log ==="]
        any_entry = False
        for rider in riders:
            for entry in rider.log:
                any_entry = True
                order = "-" if entry["order_id"] is None else entry["order_id"]
                lines.append(
                    "  t=%d rider=%d event=%s order=%s pos=(%d,%d) state=%s"
                    % (entry["time"], entry["rider_id"], entry["event"], order,
                       entry["x"], entry["y"],
                       STATE_NAMES.get(entry["state"], "unknown"))
                )
        if not any_entry:
            lines.append("  No rider events yet.")
        return "\n".join(lines)

    @staticmethod
    def _segment_indices(a, b):
        """Map character indices along an axis-aligned segment.

        Args:
            a: Start point ``(x, y)``.
            b: End point ``(x, y)``.

        Returns:
            list[tuple[int, int]]: (row, col) indices along the segment.
        """
        r1, c1 = _idx(a[1]), _idx(a[0])
        r2, c2 = _idx(b[1]), _idx(b[0])
        cells = []
        if c1 == c2:
            step = 1 if r2 >= r1 else -1
            for r in range(r1, r2 + step, step):
                cells.append((r, c1))
        else:
            step = 1 if c2 >= c1 else -1
            for c in range(c1, c2 + step, step):
                cells.append((r1, c))
        return cells

    def render_map(self, riders=None, orders=None, route=None):
        """Render the ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street,
        '.' empty space, '*' planned route. Riders are drawn on top.

        Args:
            riders: Optional iterable of Rider objects to show.
            orders: Optional iterable of Order objects whose restaurant and
                customer points should be shown (completed orders are skipped).
            route: Optional list of route corner points to draw.

        Returns:
            str: Rendered map with a legend.
        """
        canvas = [["." for _ in range(MAP_CHARS)] for _ in range(MAP_CHARS)]
        for row in range(MAP_CHARS):
            for col in range(MAP_CHARS):
                x, y = col * STEP, row * STEP
                if PathPlanner.is_on_street(x, y):
                    canvas[row][col] = "#"

        if route:
            for a, b in zip(route, route[1:]):
                for row, col in self._segment_indices(a, b):
                    canvas[row][col] = "*"
            if len(route) == 1:
                canvas[_idx(route[0][1])][_idx(route[0][0])] = "*"

        for order in orders or []:
            if order.status == "completed":
                continue
            rx, ry = order.res_pos
            canvas[_idx(ry)][_idx(rx)] = "S"
            cx, cy = order.cus_pos
            canvas[_idx(cy)][_idx(cx)] = "C"

        for rider in riders or []:
            canvas[_idx(rider.y)][_idx(rider.x)] = "R"

        lines = ["     " + "".join(str((c * STEP // 100) % 10)
                                    for c in range(MAP_CHARS))]
        for row in range(MAP_CHARS):
            lines.append("%4d " % (row * STEP) + "".join(canvas[row]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "#=Street .=Empty *=Route (1 char = %d units)" % STEP)
        return "\n".join(lines)
