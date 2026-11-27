"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import PathPlanner
from rider import STATE_NAMES

MAP_CELLS = 16
CELL = 50


def _cell(v):
    return max(0, min(MAP_CELLS - 1, int(v) // CELL))


class DisplayManager:
    """Renders text views of the simulation state."""

    def status(self):
        lines = ["Time: %d" % (globalvar.get_value("time", 0) or 0),
                 "Funds: %d" % (globalvar.get_value("funds", 0) or 0)]
        riders = globalvar.get_value("riders") or []
        lines.append("Riders: %d" % len(riders))
        for r in riders:
            lines.append("  Rider %s at (%d, %d) state=%s speed=%d orders=%d "
                         "active=%d%s" % (
                             r.rider_id, r.x, r.y,
                             STATE_NAMES.get(r.state, r.state), r.speed,
                             len(r.orders), len(r.active_orders()),
                             " [special]" if r.special_case else ""))
            for o in r.orders:
                lines.append("    #%d %s -> %s [%s]" % (o.id, o.res_pos,
                                                       o.cus_pos, o.status))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-6d %-12s %-12s %-6d %-6s %-6s %s" % (
                o.id, o.created_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if taken is None else str(taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        return "\n".join(lines)

    def riders_log(self):
        riders = globalvar.get_value("riders") or []
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %s:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s order=%-4s at (%s, %s)" % (
                    e.get("time"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    e.get("x"), e.get("y")))
        return "\n".join(lines)

    def render_map(self, route=None, highlight_order=None):
        grid = []
        for row in range(MAP_CELLS):
            line = []
            for col in range(MAP_CELLS):
                line.append("#" if row % 2 == 0 or col % 2 == 0 else ".")
            grid.append(line)
        if route:
            for i in range(len(route) - 1):
                (x1, y1), (x2, y2) = route[i], route[i + 1]
                if x1 == x2:
                    for c in range(min(_cell(y1), _cell(y2)),
                                   max(_cell(y1), _cell(y2)) + 1):
                        grid[c][_cell(x1)] = "*"
                else:
                    for c in range(min(_cell(x1), _cell(x2)),
                                   max(_cell(x1), _cell(x2)) + 1):
                        grid[_cell(y1)][c] = "*"
        orders = globalvar.get_value("orders") or []
        for o in orders:
            if o.status == "completed" and o is not highlight_order:
                continue
            grid[_cell(o.res_pos[1])][_cell(o.res_pos[0])] = "S"
            grid[_cell(o.cus_pos[1])][_cell(o.cus_pos[0])] = "C"
        for r in globalvar.get_value("riders") or []:
            grid[_cell(r.y)][_cell(r.x)] = "R"
        header = "   " + "".join("%-2d" % (c * CELL // 100 * 1)
                                 if c % 2 == 0 else "  "
                                 for c in range(MAP_CELLS))
        lines = [header.rstrip()]
        for i, row in enumerate(grid):
            label = "%d" % (i * CELL // 100) if i % 2 == 0 else " "
            lines.append("%2s " % label + " ".join(row))
        lines.append("Legend: R=rider S=restaurant C=customer *=route "
                     "#=street .=empty (cell=50 units, labels in hundreds)")
        return "\n".join(lines)

    def start_result(self, result):
        o = result["order"]
        r = result["rider"]
        lines = [
            "Order #%d created." % o.id,
            "Restaurant grid position: (%d, %d)" % o.res_pos,
            "Customer grid position:   (%d, %d)" % o.cus_pos,
            "New rider added: %s" % ("yes (%s)" % ", ".join(
                str(h.rider_id) for h in result["hired"])
                if result["new_rider"] else "no"),
            "Assigned rider: %s at (%d, %d), speed %d units/tick" % (
                r.rider_id, r.x, r.y, r.speed),
            "Route: " + " -> ".join("(%d,%d)" % p for p in result["route"]),
            "Route length: %d units, estimated time: %d ticks" % (
                result["distance"], result["estimated_time"]),
            self.render_map(result["route"], o),
        ]
        return "\n".join(lines)
