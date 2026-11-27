"""Status display and ASCII map visualisation."""

try:
    from . import config, globalvar
except ImportError:  # pragma: no cover
    import config
    import globalvar


class DisplayManager:
    """Formats system state into human readable text."""

    def __init__(self, system, map_size=config.DISPLAY_SIZE):
        self.system = system
        self.map_size = map_size
        self.unit = config.MAP_SIZE // map_size  # 50 units per character

    # map ------------------------------------------------------------------
    def _cell(self, x, y):
        c = min(max(int(x) // self.unit, 0), self.map_size - 1)
        r = min(max(int(y) // self.unit, 0), self.map_size - 1)
        return r, c

    def _base_grid(self):
        grid = []
        for r in range(self.map_size):
            row = []
            for c in range(self.map_size):
                street = (r * self.unit) % config.CELL_SIZE == 0 or \
                    (c * self.unit) % config.CELL_SIZE == 0
                row.append('#' if street else '.')
            grid.append(row)
        return grid

    def _draw_line(self, grid, a, b, ch='*'):
        r1, c1 = self._cell(*a)
        r2, c2 = self._cell(*b)
        # axis-aligned: horizontal then vertical
        step = 1 if c2 >= c1 else -1
        for c in range(c1, c2 + step, step):
            grid[r1][c] = ch
        step = 1 if r2 >= r1 else -1
        for r in range(r1, r2 + step, step):
            grid[r][c2] = ch

    def render_map(self, route=None, highlight=None):
        """Return the 16x16 ASCII map as a string.

        'R' rider, 'S' restaurant, 'C' customer, '#' street, '.' empty,
        '*' planned route.
        """
        grid = self._base_grid()
        if route:
            for a, b in zip(route, route[1:]):
                self._draw_line(grid, a, b)
        for o in globalvar.get_value("orders") or []:
            if o.status == "completed":
                continue
            r, c = self._cell(*o.restaurant)
            grid[r][c] = 'S'
            r, c = self._cell(*o.customer)
            grid[r][c] = 'C'
        for rider in self.system.riders:
            r, c = self._cell(rider.x, rider.y)
            grid[r][c] = 'R'
        if highlight is not None:
            r, c = self._cell(highlight.x, highlight.y)
            grid[r][c] = 'R'
        header = "   " + "".join("%X" % (c % 16) for c in range(self.map_size))
        lines = [header]
        for i, row in enumerate(grid):
            lines.append("%2X " % i + "".join(row))
        lines.append("Legend: R=rider S=restaurant C=customer #=street "
                     ".=empty *=route (1 char = %d units)" % self.unit)
        return "\n".join(lines)

    # reports --------------------------------------------------------------
    def status_text(self):
        s = self.system
        lines = ["=== System status (tick %d) ===" % s.current_tick,
                 "Funds: %d" % s.funds,
                 "Riders: %d" % len(s.riders)]
        for r in s.riders:
            ids = [str(getattr(o, "id", "?")) for o in r.orders]
            active = [str(o.id) for o in r.active_orders()]
            lines.append("  Rider %d @ (%d, %d) speed=%d state=%s "
                         "orders=%d active=[%s] all=[%s]"
                         % (r.rider_id, r.x, r.y, r.speed, r.state_name,
                            len(r.orders), ", ".join(active), ", ".join(ids)))
        pending = s.order_manager.pending_orders()
        lines.append("Pending (unassigned) orders: %d" % len(pending))
        return "\n".join(lines)

    def orders_text(self):
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-9s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Time",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken if o.time_taken is not None else "-"
            lines.append("%-4d %-6s %-12s %-12s %-9.1f %-6s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.restaurant,
                "(%d,%d)" % o.customer, float(o.distance), taken,
                o.rider_id if o.rider_id is not None else "-", o.status))
        return "\n".join(lines)

    def riders_text(self):
        if not self.system.riders:
            return "No riders yet."
        names = {0: "idle", 1: "picking up", 2: "delivering"}
        lines = []
        for r in self.system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s pos=(%s, %s) order=%s state=%s"
                             % (e.get("time"), e.get("event"), e.get("x"),
                                e.get("y"),
                                e.get("order_id") if e.get("order_id")
                                is not None else "-",
                                names.get(e.get("state"), e.get("state"))))
        return "\n".join(lines)

    def start_result_text(self, info):
        o = info["order"]
        lines = ["Order %d created." % o.id,
                 "Restaurant grid position: (%d, %d)" % o.restaurant,
                 "Customer grid position:   (%d, %d)" % o.customer]
        rec = info.get("recruited")
        lines.append("New rider added: %s" % (
            "yes (rider %d, funds now %d)" % (rec.rider_id, self.system.funds)
            if rec is not None else "no"))
        rider = info.get("rider")
        if rider is None:
            lines.append("No rider available; order remains pending.")
            return "\n".join(lines)
        lines.append("Assigned rider: %d (speed %d units/tick)"
                     % (rider.rider_id, rider.speed))
        lines.append("Estimated time to complete queued route: %s ticks"
                     % info.get("estimated_time"))
        lines.append("Route: " + " -> ".join(
            "(%d,%d)" % p for p in info.get("route", [])))
        lines.append(self.render_map(info.get("route"), rider))
        return "\n".join(lines)
