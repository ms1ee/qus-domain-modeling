"""Display manager."""

import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text output helpers."""

    def _canvas(self):
        n = 17
        c = [["#"] * n for _ in range(n)]
        for i in range(1, n, 2):
            for j in range(1, n, 2):
                c[i][j] = "."
        return c

    @staticmethod
    def _idx(v):
        return max(0, min(16, int(round(v / 50.0))))

    def render_map(self, route=None):
        c = self._canvas()
        if route:
            for a, b in zip(route, route[1:]):
                x0, y0, x1, y1 = (self._idx(a[0]), self._idx(a[1]),
                                  self._idx(b[0]), self._idx(b[1]))
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    for y in range(min(y0, y1), max(y0, y1) + 1):
                        c[y][x] = "-" if y0 == y1 else "|"
        for o in globalvar.get_value("orders", []) or []:
            if o.status == "completed":
                continue
            if o.status in ("pending", "assigned"):
                c[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = "S"
            c[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = "C"
        for r in globalvar.get_value("riders", []) or []:
            c[self._idx(r.y)][self._idx(r.x)] = "R"
        return "\n".join("".join(row) for row in c)

    def route_info(self, rider, order):
        pts = [rider.pos] + PathPlanner.route(rider.pos, order.res_pos)[1:]
        pts += PathPlanner.route(order.res_pos, order.cus_pos)[1:]
        dist = sum(PathPlanner.distance(a, b) for a, b in zip(pts, pts[1:]))
        t = -(-dist // rider.speed) if rider.speed else 0
        return pts, dist, t

    def status(self):
        lines = ["Time: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(globalvar.get_value("riders", [])))]
        for r in globalvar.get_value("riders", []):
            lines.append("Rider %d at (%d,%d) speed=%d state=%s orders=%s" % (
                r.rider_id, r.x, r.y, r.speed, STATES[r.state],
                [o.id for o in r.orders]))
        lines.append(self.render_map())
        return "\n".join(lines)

    def orders(self):
        os_ = globalvar.get_value("orders", [])
        if not os_:
            return "No orders."
        lines = []
        for o in os_:
            d = o.duration
            lines.append("Order %d start=%s restaurant=%s customer=%s "
                         "distance=%d time=%s rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, d if d is not None else "-",
                             o.rider_id if o.rider_id else "-", o.status))
        return "\n".join(lines)

    def riders(self):
        lines = []
        for r in globalvar.get_value("riders", []):
            for e in r.log:
                lines.append("Rider %d t=%s %s order=%s at (%d,%d)" % (
                    r.rider_id, e["time"], e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(lines) or "No riders."
