"""Display manager."""
import globalvar

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering of status and map."""

    SIZE = 16

    def _cell(self, x, y):
        return (min(self.SIZE - 1, max(0, y // 50)),
                min(self.SIZE - 1, max(0, x // 50)))

    def render_map(self, route=None):
        grid = [["#" if (i % 2 == 0 or j % 2 == 0) and False else "."
                 for j in range(self.SIZE)] for i in range(self.SIZE)]
        for i in range(self.SIZE):
            for j in range(self.SIZE):
                if i % 2 == 0 and j % 2 == 0:
                    grid[i][j] = "#"
        if route:
            for (x1, y1), (x2, y2) in zip(route, route[1:]):
                steps = max(abs(x2 - x1), abs(y2 - y1)) // 25 + 1
                for s in range(steps + 1):
                    x = x1 + (x2 - x1) * s // steps
                    y = y1 + (y2 - y1) * s // steps
                    i, j = self._cell(x, y)
                    grid[i][j] = "*"
        for o in globalvar.get_value("orders", []):
            if o.status != "completed":
                i, j = self._cell(*o.res_pos)
                grid[i][j] = "S"
                i, j = self._cell(*o.cus_pos)
                grid[i][j] = "C"
        for r in globalvar.get_value("riders", []):
            i, j = self._cell(r.x, r.y)
            grid[i][j] = "R"
        return "\n".join("".join(row) for row in grid)

    def status(self):
        riders = globalvar.get_value("riders", [])
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s, %d order(s): %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state], len(r.orders),
                [(o.id, o.status) for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders", [])
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            lines.append(
                "Order %d: start=%d restaurant=%s customer=%s dist=%.1f "
                "time_taken=%s rider=%s status=%s" % (
                    o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                    o.time_taken if o.time_taken is not None else "-",
                    o.rider_id if o.rider_id is not None else "-", o.status))
        return "\n".join(lines)

    def rider_logs(self):
        lines = []
        for r in globalvar.get_value("riders", []):
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%d %s at (%d,%d) order=%s" % (
                    e["time"], e["event"], e["x"], e["y"],
                    e["order_id"] if e["order_id"] is not None else "-"))
        return "\n".join(lines) if lines else "No riders."
