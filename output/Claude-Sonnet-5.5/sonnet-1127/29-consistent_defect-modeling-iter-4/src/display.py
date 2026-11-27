"""Display manager."""
from path_planner import PathPlanner

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}
SIZE = 16
UNIT = 50


def _cell(v):
    return max(0, min(SIZE - 1, int(v) // UNIT))


class DisplayManager:
    """Textual status and ASCII map rendering."""

    def render_map(self, riders=(), orders=(), route=None):
        grid = [["." for _ in range(SIZE)] for _ in range(SIZE)]
        if route:
            for a, b in zip(route, route[1:]):
                x0, y0 = _cell(a[0]), _cell(a[1])
                x1, y1 = _cell(b[0]), _cell(b[1])
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    for y in range(min(y0, y1), max(y0, y1) + 1):
                        grid[y][x] = "#"
        for o in orders:
            if o.status != "completed":
                grid[_cell(o.res_pos[1])][_cell(o.res_pos[0])] = "S"
                grid[_cell(o.cus_pos[1])][_cell(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_cell(r.y)][_cell(r.x)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    def route_text(self, rider, order):
        pl = PathPlanner()
        route = pl.plan_multi((rider.x, rider.y), [order.res_pos, order.cus_pos])
        length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                     for a, b in zip(route, route[1:]))
        t = -(-length // rider.speed)
        return (self.render_map([rider], [order], route)
                + "\nRoute: %s\nSpeed: %d units/tick, estimated time: %d ticks"
                % (" -> ".join(map(str, route)), rider.speed, t))

    def status_text(self, system):
        lines = ["Tick: %d  Funds: %d  Riders: %d"
                 % (system.tick, system.funds, len(system.riders))]
        for r in system.riders:
            lines.append("Rider %d at (%d,%d) state=%s orders=%s"
                         % (r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                            [(o.id, o.status) for o in r.orders]))
        lines.append(self.render_map(system.riders, system.orders))
        return "\n".join(lines)

    def orders_text(self, system):
        if not system.orders:
            return "No orders."
        return "\n".join(
            "Order %d start=%d restaurant=%s customer=%s distance=%s time=%s rider=%s status=%s"
            % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
               o.time_taken, o.rider_id, o.status) for o in system.orders)

    def riders_text(self, system):
        lines = []
        for r in system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%d (%d,%d) state=%d event=%s order=%s"
                             % (e["time"], e["x"], e["y"], e["state"],
                                e["event"], e["order_id"]))
        return "\n".join(lines) or "No riders."
