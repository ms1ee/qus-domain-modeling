"""Status display and ASCII map visualisation."""

from path_planner import planner, MAP_SIZE
from rider import STATE_NAMES

STEP = 50


class DisplayManager:
    """Formats status, order and rider information for the console.

    Map symbols:
      ``+`` intersection, ``-``/``|`` streets, ``.`` empty block,
      ``R``/``C`` restaurant/customer of the highlighted order,
      ``r``/``c`` other active restaurants/customers,
      ``*`` planned route, ``P``/``D`` pickup/drop-off points,
      digits: riders (id modulo 10).
    The y axis grows downward (y=0 at the top).
    """

    LEGEND = ("Legend: +=intersection -|=street .=block R/C=restaurant/"
              "customer (r/c other orders) *=route P/D=pickup/drop-off "
              "0-9=rider id%10")

    @staticmethod
    def _base_char(x, y):
        """Background map character for point (x, y)."""
        g = planner.grid_size
        if x % g == 0 and y % g == 0:
            return "+"
        if y % g == 0:
            return "-"
        if x % g == 0:
            return "|"
        return "."

    @staticmethod
    def _idx(v):
        """Map coordinate to character index."""
        n = MAP_SIZE // STEP
        return max(0, min(n, int(round(v / STEP))))

    def render_map(self, riders=None, orders=None, route=None,
                   highlight=None):
        """Return the ASCII map as a string."""
        n = MAP_SIZE // STEP + 1
        grid = [[self._base_char(i * STEP, j * STEP) for i in range(n)]
                for j in range(n)]
        if route and route.get("waypoints"):
            pts = route["waypoints"]
            for a, b in zip(pts, pts[1:]):
                x0, y0, x1, y1 = (self._idx(a[0]), self._idx(a[1]),
                                  self._idx(b[0]), self._idx(b[1]))
                for i in range(min(x0, x1), max(x0, x1) + 1):
                    grid[y0][i] = "*"
                for j in range(min(y0, y1), max(y0, y1) + 1):
                    grid[j][x1] = "*"
            p, d = route.get("pickup"), route.get("dropoff")
            if p:
                grid[self._idx(p[1])][self._idx(p[0])] = "P"
            if d:
                grid[self._idx(d[1])][self._idx(d[0])] = "D"
        for o in orders or []:
            if o.status == "completed" and o is not highlight:
                continue
            hi = o is highlight
            grid[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = \
                "R" if hi else "r"
            grid[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = \
                "C" if hi else "c"
        for r in riders or []:
            grid[self._idx(r.y)][self._idx(r.x)] = str(r.rider_id % 10)
        header = "      " + " ".join(
            str(i * STEP // 100) if i % 2 == 0 else " " for i in range(n))
        lines = ["x(x100) ->", header]
        for j, row in enumerate(grid):
            label = "%4d " % (j * STEP) if j % 2 == 0 else "     "
            lines.append(label + " " + " ".join(row))
        lines.append(self.LEGEND)
        return "\n".join(lines)

    def format_status(self, system, pending_count=0):
        """System snapshot: funds, time and all riders."""
        riders = system.riders
        lines = ["=== System Status (tick %d) ===" % system.time,
                 "Funds: %d" % system.funds,
                 "Riders: %d" % len(riders),
                 "Pending (unassigned) orders: %d" % pending_count]
        for r in riders:
            ids = [o.id for o in r.orders]
            lines.append(
                "  Rider %d @ (%d,%d) speed=%d state=%d(%s) orders=%d %s%s"
                % (r.rider_id, r.x, r.y, r.speed, r.state,
                   STATE_NAMES.get(r.state, "?"), len(r.orders), ids,
                   " [special case]" if r.special_case else ""))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-8s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")]
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            lines.append("%-4d %-6d %-11s %-11s %-6d %-8s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance, taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """Chronological list of rider status changes."""
        entries = []
        for r in riders:
            entries.extend(r.log)
        if not entries:
            return "No rider events yet."
        entries.sort(key=lambda e: (e.get("time", 0), e.get("rider_id", 0)))
        lines = ["%-6s %-6s %-22s %-11s %-6s" % ("Time", "Rider", "Event",
                                                "Location", "Order")]
        for e in entries:
            lines.append("%-6d %-6s %-22s %-11s %-6s" % (
                e.get("time", 0), e.get("rider_id"), e["event"],
                "(%d,%d)" % (e.get("x", 0), e.get("y", 0)),
                "-" if e["order_id"] is None else e["order_id"]))
        return "\n".join(lines)

    def format_start_result(self, result, system):
        """Describe the result of an order creation."""
        order, rider = result["order"], result["rider"]
        lines = ["Order %d created." % order.id,
                 "Restaurant grid position: (%d,%d) cell %s" % (
                     order.res_pos + (planner.grid_index(order.res_pos),)),
                 "Customer grid position:   (%d,%d) cell %s" % (
                     order.cus_pos + (planner.grid_index(order.cus_pos),))]
        if result["new_rider"] is not None:
            lines.append("New rider added: yes (rider %d, funds now %d)" % (
                result["new_rider"].rider_id, system.funds))
        else:
            lines.append("New rider added: no")
        if rider is None:
            lines.append("No rider available; order queued.")
            return "\n".join(lines)
        route = result["route"]
        lines.append("Assigned rider: %d at (%d,%d), speed %d units/tick" % (
            rider.rider_id, rider.x, rider.y, rider.speed))
        if result["queued_behind"]:
            lines.append("Queued behind %d order(s) of this rider." %
                         result["queued_behind"])
        lines.append("Route length: %d (pickup %d + delivery %d), "
                     "estimated time: %d ticks" % (
                         route["total"], route["pickup_length"],
                         route["delivery_length"], result["eta"]))
        lines.append("Route: " + " -> ".join(
            "(%d,%d)" % p for p in route["waypoints"]))
        lines.append(self.render_map(system.riders, [order], route, order))
        return "\n".join(lines)
