"""Status displays and ASCII map visualisation."""

from rider import RiderState

CANVAS = 17  # 8 cells + 9 street lines


class DisplayManager:
    """Builds textual views of the simulation."""

    @staticmethod
    def _pos(x, y):
        row = min(CANVAS - 1, max(0, int(round(y / 50.0))))
        col = min(CANVAS - 1, max(0, int(round(x / 50.0))))
        return row, col

    @staticmethod
    def _base():
        canvas = []
        for r in range(CANVAS):
            row = []
            for c in range(CANVAS):
                row.append('#' if (r % 2 == 0 or c % 2 == 0) else '.')
            canvas.append(row)
        return canvas

    @staticmethod
    def _mark(canvas, r, c, ch):
        cur = canvas[r][c]
        if cur in '-|+' and cur != ch:
            canvas[r][c] = '+'
        else:
            canvas[r][c] = ch

    def _draw_route(self, canvas, points):
        cells = [self._pos(x, y) for x, y in points]
        for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
            if r1 != r2 and c1 != c2:
                corner = (r1, c2)
                segs = [((r1, c1), corner), (corner, (r2, c2))]
            else:
                segs = [((r1, c1), (r2, c2))]
            for (a_r, a_c), (b_r, b_c) in segs:
                if a_r == b_r:
                    step = 1 if b_c >= a_c else -1
                    for c in range(a_c, b_c + step, step):
                        self._mark(canvas, a_r, c, '-')
                else:
                    step = 1 if b_r >= a_r else -1
                    for r in range(a_r, b_r + step, step):
                        self._mark(canvas, r, a_c, '|')
        for r, c in cells[1:-1]:
            canvas[r][c] = '+'

    def render_map(self, riders, orders, route_points=None, highlight_rider=None):
        """Render the 8x8 grid map as ASCII text.

        Symbols: R rider, S restaurant, C customer, . empty, # street,
        - | + route segments.
        """
        canvas = self._base()
        if route_points and len(route_points) > 1:
            self._draw_route(canvas, route_points)
        for order in orders:
            if order.is_completed():
                continue
            r, c = self._pos(*order.res_pos)
            canvas[r][c] = 'S'
            r, c = self._pos(*order.cus_pos)
            canvas[r][c] = 'C'
        for rider in riders:
            if highlight_rider is not None and rider is not highlight_rider:
                continue
            r, c = self._pos(rider.x, rider.y)
            canvas[r][c] = 'R'
        lines = ["    " + " ".join(str(c // 2) if c % 2 == 0 else ' ' for c in range(CANVAS))
                 + "   (x100)"]
        for r in range(CANVAS):
            label = str(r // 2) if r % 2 == 0 else ' '
            lines.append(" {}  ".format(label) + " ".join(canvas[r]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer .=Empty #=Street -|+=Route")
        return "\n".join(lines)

    @staticmethod
    def status_text(system):
        """System snapshot: funds, tick and rider states."""
        riders = system.riders
        lines = [
            "=== System Status (tick {}) ===".format(system.current_tick),
            "Funds: {}".format(system.funds),
            "Riders: {}".format(len(riders)),
        ]
        for r in riders:
            lines.append("  Rider #{:<3} pos=({:>3},{:>3}) state={:<11} orders={} {}".format(
                r.rider_id, r.x, r.y, RiderState.name(r.state), len(r.orders),
                [o.id for o in r.orders]))
        pending = system.order_manager.pending_orders()
        lines.append("Pending (unassigned) orders: {}".format(len(pending)))
        return "\n".join(lines)

    @staticmethod
    def orders_text(orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        header = "{:<5} {:<6} {:<12} {:<12} {:<9} {:<6} {:<6} {:<11}".format(
            "ID", "Start", "Restaurant", "Customer", "Distance", "Taken", "Rider", "Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            lines.append("{:<5} {:<6} {:<12} {:<12} {:<9} {:<6} {:<6} {:<11}".format(
                o.id, o.start_time, "({},{})".format(*o.res_pos), "({},{})".format(*o.cus_pos),
                o.distance, "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    @staticmethod
    def riders_log_text(riders):
        """Every recorded status change of every rider."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #{} (speed {}):".format(r.rider_id, r.speed))
            for e in r.log:
                lines.append("  t={:<5} {:<22} pos=({},{}) order={} state={}".format(
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    RiderState.name(e.get("state"))))
        return "\n".join(lines)
