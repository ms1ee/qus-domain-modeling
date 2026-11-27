"""Status display and ASCII map visualisation."""

import globalvar
from config import MAP_SIZE
from rider import STATE_NAMES

STEP = 50
N = MAP_SIZE // STEP + 1  # 17 points per axis

LEGEND = ("Legend: R=restaurant  C=customer  0-9=rider (id mod 10)  *=route  "
          "+=intersection  -,|=street  .=block  (labels = coordinate/100)")


def _idx(v):
    return max(0, min(N - 1, (int(v) + STEP // 2) // STEP))


class DisplayManager:
    """Builds text output for statuses, orders, rider logs and maps."""

    def __init__(self, system_manager):
        self.system = system_manager

    # ------------------------------------------------------------------ map
    def render_map(self, route_start=None, route=None, highlight_order=None):
        """Render an ASCII map (8x8 grid) with riders, orders and a route."""
        grid = []
        for i in range(N):
            row = []
            for j in range(N):
                x, y = j * STEP, i * STEP
                if x % 100 == 0 and y % 100 == 0:
                    row.append("+")
                elif y % 100 == 0:
                    row.append("-")
                elif x % 100 == 0:
                    row.append("|")
                else:
                    row.append(".")
            grid.append(row)

        if route_start is not None and route:
            cur = route_start
            for wp in route:
                self._draw_segment(grid, cur, wp)
                cur = wp

        orders = [o for o in (globalvar.get_value("orders") or []) if o.status != "completed"]
        if highlight_order is not None and highlight_order not in orders:
            orders.append(highlight_order)
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "R"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in self.system.riders:
            grid[_idx(r.y)][_idx(r.x)] = str(r.rider_id % 10)

        lines = []
        header = "    " + " ".join(str(j // 2) if j % 2 == 0 else " " for j in range(N))
        lines.append(header)
        for i, row in enumerate(grid):
            label = str(i // 2) if i % 2 == 0 else " "
            lines.append(" %s  %s" % (label, " ".join(row)))
        lines.append(LEGEND)
        return "\n".join(lines)

    @staticmethod
    def _draw_segment(grid, a, b):
        x0, y0 = _idx(a[0]), _idx(a[1])
        x1, y1 = _idx(b[0]), _idx(b[1])
        if x0 == x1:
            for i in range(min(y0, y1), max(y0, y1) + 1):
                grid[i][x0] = "*"
        elif y0 == y1:
            for j in range(min(x0, x1), max(x0, x1) + 1):
                grid[y0][j] = "*"
        else:
            for j in range(min(x0, x1), max(x0, x1) + 1):
                grid[y0][j] = "*"
            for i in range(min(y0, y1), max(y0, y1) + 1):
                grid[i][x1] = "*"

    # --------------------------------------------------------------- status
    def status_text(self):
        """Snapshot of funds, riders and orders."""
        orders = globalvar.get_value("orders") or []
        done = sum(1 for o in orders if o.status == "completed")
        lines = ["=== System Status (tick %d) ===" % self.system.time,
                 "Funds: %d" % self.system.funds,
                 "Riders: %d" % len(self.system.riders)]
        for r in self.system.riders:
            lines.append("  Rider %d | pos (%d, %d) | speed %d | %s | orders: %s | special: %s"
                         % (r.rider_id, r.x, r.y, r.speed, STATE_NAMES.get(r.state, "?"),
                            [o.id for o in r.orders] or "[]",
                            "yes" if r.special_case else "no"))
        lines.append("Orders: total %d, active %d, completed %d"
                     % (len(orders), len(orders) - done, done))
        lines.append(self.render_map())
        return "\n".join(lines)

    def orders_text(self):
        """Table of all orders."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-11s %-6s %-12s %-12s %-8s %-6s %-6s"
                 % ("ID", "Status", "Start", "Restaurant", "Customer", "Distance", "Time", "Rider")]
        for o in orders:
            lines.append("%-4d %-11s %-6d %-12s %-12s %-8d %-6s %-6s" % (
                o.id, o.status, o.create_time,
                "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else str(o.time_taken),
                "-" if o.rider_id is None else str(o.rider_id)))
        return "\n".join(lines)

    def riders_log_text(self):
        """All recorded rider status changes."""
        if not self.system.riders:
            return "No riders yet."
        lines = []
        for r in self.system.riders:
            lines.append("Rider %d (%s, %d delivered):" % (r.rider_id, r.state_name, r.delivered_count))
            for e in r.log:
                lines.append("  t=%-5s %-22s pos (%s, %s)  order %s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "-" if e.get("order_id") is None else e.get("order_id")))
        return "\n".join(lines)

    def order_result_text(self, result):
        """Output for the 'start' command."""
        o, r = result["order"], result["rider"]
        lines = [
            "Order %d created." % o.id,
            "Restaurant: input (%d, %d) -> grid (%d, %d) cell [%d,%d]" % (
                o.raw_res[0], o.raw_res[1], o.res_pos[0], o.res_pos[1],
                o.res_pos[0] // 100, o.res_pos[1] // 100),
            "Customer:   input (%d, %d) -> grid (%d, %d) cell [%d,%d]" % (
                o.raw_cus[0], o.raw_cus[1], o.cus_pos[0], o.cus_pos[1],
                o.cus_pos[0] // 100, o.cus_pos[1] // 100),
            "New rider added: %s" % (
                "yes (rider %d)" % result["recruited"].rider_id if result["recruited"] else "no"),
            "Assigned rider: %d at (%d, %d), speed %d units/tick" % (r.rider_id, r.x, r.y, r.speed),
            "Route length: %d units, estimated time: %d ticks" % (
                result["route_length"], result["est_ticks"]),
            "Route: %s" % " -> ".join("(%d,%d)" % p for p in [tuple(result["route_start"])] + result["route"]),
            self.render_map(result["route_start"], result["route"], o),
        ]
        return "\n".join(lines)
