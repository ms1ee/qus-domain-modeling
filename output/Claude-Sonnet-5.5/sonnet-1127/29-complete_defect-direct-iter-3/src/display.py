"""Display manager."""
from src import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Renders status and ASCII map."""

    @staticmethod
    def render_map(route=None, riders=None, orders=None):
        """17x17 canvas at 50-unit resolution; streets are '#'."""
        n = 17
        c = [["#" if (i % 2 == 0 or j % 2 == 0) else "." for j in range(n)]
             for i in range(n)]

        def idx(p):
            return (min(16, max(0, p[0] // 50)), min(16, max(0, p[1] // 50)))
        if route:
            for a, b in zip(route, route[1:]):
                ax, ay = idx(a)
                bx, by = idx(b)
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    for y in range(min(ay, by), max(ay, by) + 1):
                        c[y][x] = "*"
        for o in orders or []:
            if o.status != "completed":
                x, y = idx(o.res_pos)
                c[y][x] = "S"
                x, y = idx(o.cus_pos)
                c[y][x] = "C"
        for r in riders or []:
            x, y = idx((r.x, r.y))
            c[y][x] = "R"
        return "\n".join("".join(row) for row in c)

    def status(self):
        """System snapshot text."""
        riders = globalvar.get_value("riders")
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) speed %d state=%s orders=%s"
                         % (r.rider_id, r.x, r.y, r.speed, STATES[r.state],
                            [o.id for o in r.orders]))
        lines.append(self.render_map(riders=riders,
                                     orders=globalvar.get_value("orders")))
        return "\n".join(lines)

    def orders(self):
        """Order details text."""
        out = []
        for o in globalvar.get_value("orders"):
            d = o.duration
            out.append("Order %d start=%d restaurant=%s customer=%s "
                       "distance=%d time=%s rider=%s status=%s" % (
                           o.id, o.start_time, o.res_pos, o.cus_pos,
                           o.distance, d if d is not None else "-",
                           o.rider_id, o.status))
        return "\n".join(out) or "No orders."

    def riders_log(self):
        """Rider event history text."""
        out = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                out.append("Rider %d t=%s %s order=%s at (%d,%d)" % (
                    r.rider_id, e["time"], e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(out) or "No rider events."
