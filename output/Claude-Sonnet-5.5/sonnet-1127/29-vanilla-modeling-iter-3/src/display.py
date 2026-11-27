"""Display manager."""
import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    def render_map(self, route=None):
        grid = [["." for _ in range(8)] for _ in range(8)]

        def cell(p):
            return (min(7, max(0, p[1] // 100)), min(7, max(0, p[0] // 100)))

        if route:
            for a, b in zip(route.waypoints, route.waypoints[1:]):
                (r1, c1), (r2, c2) = cell(a), cell(b)
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        grid[r][c] = "#"
        for o in globalvar.get_value("orders") or []:
            if o.status != "completed":
                r, c = cell(o.res_pos)
                grid[r][c] = "S"
                r, c = cell(o.cus_pos)
                grid[r][c] = "C"
        for rd in globalvar.get_value("riders") or []:
            r, c = cell((rd.x, rd.y))
            grid[r][c] = "R"
        return "\n".join(" ".join(row) for row in grid)

    def status(self):
        riders = globalvar.get_value("riders")
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            lines.append(
                "Order %d start=%s from=%s to=%s dist=%.1f time=%s rider=%s [%s]"
                % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                   o.time_taken if o.time_taken is not None else "-",
                   o.rider_id if o.rider_id is not None else "-", o.status))
        return "\n".join(lines)

    def riders_history(self):
        lines = []
        for r in globalvar.get_value("riders"):
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%d (%d,%d) state=%s event=%s order=%s" % (
                    e["time"], e["x"], e["y"], STATES[e["state"]],
                    e["event"], e["order_id"]))
        return "\n".join(lines) if lines else "No riders."
