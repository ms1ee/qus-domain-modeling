"""Status display and ASCII map visualisation."""

import math

import globalvar
from path_planner import PathPlanner
from rider import STATE_NAMES

SIZE = 17  # 9 street lines + 8 cell rows


def _idx(v):
    return max(0, min(SIZE - 1, int(round(v / 50.0))))


class DisplayManager:
    """Builds textual displays of the simulation."""

    @staticmethod
    def _blank_map():
        grid = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                row.append("#" if (r % 2 == 0 or c % 2 == 0) else ".")
            grid.append(row)
        return grid

    @staticmethod
    def _draw_path(grid, path):
        for i in range(len(path) - 1):
            (x1, y1), (x2, y2) = path[i], path[i + 1]
            length = abs(x2 - x1) + abs(y2 - y1)
            steps = max(1, int(length // 25))
            for s in range(steps + 1):
                x = x1 + (x2 - x1) * s / steps
                y = y1 + (y2 - y1) * s / steps
                grid[_idx(y)][_idx(x)] = "*"

    @staticmethod
    def render_map(route=None, orders=None):
        """Return the ASCII map as a string."""
        grid = DisplayManager._blank_map()
        if route:
            DisplayManager._draw_path(grid, route)
        if orders is None:
            orders = [o for o in globalvar.get_value("orders") or []
                      if o.status != "completed"]
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in globalvar.get_value("riders") or []:
            grid[_idx(r.y)][_idx(r.x)] = "R"
        header = "    " + "".join(str((c // 2) % 10) if c % 2 else " "
                                  for c in range(SIZE))
        lines = [header]
        for i, row in enumerate(grid):
            label = str(i // 2) if i % 2 else " "
            lines.append(" %s  %s" % (label, "".join(row)))
        lines.append("Legend: R=rider S=restaurant C=customer *=route "
                     "#=street .=empty")
        return "\n".join(lines)

    @staticmethod
    def order_result(result):
        """Text for the result of a ``start`` command."""
        order, rider, new_rider = result["order"], result["rider"], result["new_rider"]
        lines = [
            "Order #%d created." % order.id,
            "Restaurant grid position: (%d, %d)" % order.res_pos,
            "Customer grid position:   (%d, %d)" % order.cus_pos,
            "New rider added: %s" % (
                "yes (rider #%d)" % new_rider.rider_id if new_rider else "no"),
        ]
        if rider is None:
            lines.append("No rider available; order queued as pending.")
            lines.append(DisplayManager.render_map())
            return "\n".join(lines)
        path = PathPlanner.compute_multi_path(
            [rider.position, order.res_pos, order.cus_pos])
        if rider.orders and rider.orders[0] is not order:
            path = rider.remaining_path()
        dist = PathPlanner.path_length(path)
        eta = int(math.ceil(dist / float(rider.speed))) if rider.speed else 0
        lines.append("Assigned rider: #%d at (%d, %d)" % (
            rider.rider_id, rider.x, rider.y))
        lines.append("Speed: %d units/tick, route length: %d, estimated "
                     "time: %d ticks" % (rider.speed, dist, eta))
        lines.append("Route: " + " -> ".join("(%d,%d)" % p for p in path))
        lines.append(DisplayManager.render_map(route=path))
        return "\n".join(lines)

    @staticmethod
    def status():
        """System status snapshot."""
        riders = globalvar.get_value("riders") or []
        pending = globalvar.get_value("pending_orders") or []
        lines = [
            "Time: %d" % globalvar.get_value("time", 0),
            "Funds: %d" % globalvar.get_value("funds", 0),
            "Riders: %d" % len(riders),
            "Pending (unassigned) orders: %d" % len(pending),
        ]
        for r in riders:
            lines.append("  Rider #%d pos=(%d,%d) state=%s orders=%d %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, "?"),
                len(r.orders), [o.id for o in r.orders]))
        lines.append(DisplayManager.render_map())
        return "\n".join(lines)

    @staticmethod
    def orders():
        """Details of all orders."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-6d %-6s %-6s %s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        done = [o for o in orders if o.status == "completed"]
        if done:
            avg = sum(o.time_taken for o in done) / float(len(done))
            lines.append("Completed: %d, average time: %.1f ticks" % (
                len(done), avg))
        return "\n".join(lines)

    @staticmethod
    def riders_log():
        """Status change history for all riders."""
        riders = globalvar.get_value("riders") or []
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider #%d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s order=%-4s pos=(%s,%s)" % (
                    e.get("time", "-"), e["event"],
                    "-" if e["order_id"] is None else e["order_id"],
                    e.get("x", "-"), e.get("y", "-")))
        return "\n".join(lines)
