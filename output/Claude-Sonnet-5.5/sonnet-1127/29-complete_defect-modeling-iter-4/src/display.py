"""ASCII display."""

try:
    from src import globalvar
except ImportError:  # pragma: no cover
    import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


def _ch(v):
    return max(0, min(16, int(v) // 50))


class DisplayManager:
    """Renders status and maps."""

    def render_map(self, riders=(), orders=(), route=None):
        grid = [["#" if (i % 2 == 0 or j % 2 == 0) else "."
                 for j in range(17)] for i in range(17)]
        if route:
            for a, b in zip(route, route[1:]):
                ax, ay, bx, by = _ch(a[0]), _ch(a[1]), _ch(b[0]), _ch(b[1])
                for cx in range(min(ax, bx), max(ax, bx) + 1):
                    for cy in range(min(ay, by), max(ay, by) + 1):
                        grid[cy][cx] = "*"
        for o in orders:
            if o.status != "completed":
                grid[_ch(o.res_pos[1])][_ch(o.res_pos[0])] = "S"
                grid[_ch(o.cus_pos[1])][_ch(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_ch(r.y)][_ch(r.x)] = "R"
        return "\n".join("".join(row) for row in grid)

    def status(self, riders):
        lines = ["Funds: %s" % globalvar.get_value("funds"),
                 "Tick: %s" % globalvar.get_value("tick"),
                 "Riders: %d" % len(riders)]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) speed %d state %s orders %s"
                         % (r.rider_id, r.x, r.y, r.speed, STATES[r.state],
                            [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self, orders):
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            lines.append("Order %d: start %s restaurant %s customer %s "
                         "distance %s time %s rider %s status %s"
                         % (o.id, o.start_time, o.res_pos, o.cus_pos,
                            o.distance, o.time_taken, o.rider_id, o.status))
        return "\n".join(lines)

    def riders_log(self, riders):
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%s %s order=%s pos=(%s,%s) state=%s"
                             % (e["time"], e["event"], e["order_id"],
                                e["x"], e["y"], STATES[e["state"]]))
        return "\n".join(lines) if lines else "No riders."
