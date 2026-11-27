"""Display manager."""

import globalvar
from pathplanner import PathPlanner

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    @staticmethod
    def render_map(riders=(), orders=(), route=None):
        g = [["." for _ in range(16)] for _ in range(16)]
        for i in range(16):
            for j in range(16):
                if i % 2 == 1 or j % 2 == 1:
                    g[i][j] = "#"

        def cell(p):
            return min(p[1] // 50, 15), min(p[0] // 50, 15)

        if route:
            for a, b in zip(route, route[1:]):
                (r1, c1), (r2, c2) = cell(a), cell(b)
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        g[r][c] = "*"
        for o in orders:
            if o.status != "completed":
                r, c = cell(o.res_pos)
                g[r][c] = "S"
                r, c = cell(o.cus_pos)
                g[r][c] = "C"
        for rd in riders:
            r, c = cell((rd.x, rd.y))
            g[r][c] = "R"
        return "\n".join("".join(row) for row in g)

    def show_status(self):
        riders = globalvar.get_value("riders")
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                [(o.id, o.status) for o in r.orders]))
        lines.append(self.render_map(riders, globalvar.get_value("orders")))
        return "\n".join(lines)

    @staticmethod
    def show_orders():
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        return "\n".join(
            "Order %d: start=%d restaurant=%s customer=%s dist=%.1f "
            "time=%s rider=%s status=%s" % (
                o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                o.time_taken, o.rider_id, o.status) for o in orders)

    @staticmethod
    def show_riders():
        lines = []
        for r in globalvar.get_value("riders"):
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%s (%s,%s) %s order=%s" % (
                    e.get("time"), e.get("x"), e.get("y"),
                    e["event"], e["order_id"]))
        return "\n".join(lines) or "No riders."

    def show_route(self, rider, order):
        pts = [(rider.x, rider.y), order.res_pos, order.cus_pos]
        route = PathPlanner.plan_route(pts)
        length = PathPlanner.route_length(pts)
        t = -(-length // rider.speed)
        return "%s\nSpeed: %d units/tick, length %d, estimated time %d ticks" % (
            self.render_map([rider], [order], route), rider.speed, length, t)
