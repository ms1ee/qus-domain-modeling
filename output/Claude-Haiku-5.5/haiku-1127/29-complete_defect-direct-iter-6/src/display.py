"""Text rendering for status, order history, rider logs and ASCII maps."""

from geometry import GRID_DIM, to_cell

STATE_LABELS = {0: "idle", 1: "picking up", 2: "delivering"}
_RANK = {".": 0, "#": 1, "C": 2, "S": 3, "R": 4}


class DisplayManager:
    """Builds the textual output shown by the command-line interface."""

    def render_map(self, riders, orders):
        """Render the 8x8 ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street cell
        on a rider's planned route, '.' empty. Higher-priority symbols win
        when several items share a cell.

        Args:
            riders: Iterable of Rider objects.
            orders: Iterable of Order objects (completed orders are ignored).

        Returns:
            Multi-line string.
        """
        grid = [["." for _ in range(GRID_DIM)] for _ in range(GRID_DIM)]

        def mark(col, row, symbol):
            if _RANK[symbol] > _RANK[grid[row][col]]:
                grid[row][col] = symbol

        for rider in riders:
            for point in rider.route:
                col, row = to_cell(point)
                mark(col, row, "#")
        for order in orders:
            if order.status == "completed":
                continue
            col, row = to_cell(order.res_pos)
            mark(col, row, "S")
            col, row = to_cell(order.cus_pos)
            mark(col, row, "C")
        for rider in riders:
            col, row = to_cell(rider.position)
            mark(col, row, "R")

        lines = ["     " + " ".join(str(c) for c in range(GRID_DIM))]
        for row in range(GRID_DIM):
            lines.append(f"{row * 100:>4} " + " ".join(grid[row]))
        lines.append("(row labels show the top edge y of each cell; columns show x index)")
        lines.append("Legend: R rider  S restaurant  C customer  # street  . empty")
        active = [o for o in orders if o.status != "completed"]
        if active:
            lines.append("Active orders:")
            for order in active:
                rider_text = f"rider {order.rider_id}" if order.rider_id is not None else "unassigned"
                lines.append(f"  #{order.id}: {order.status} ({rider_text})")
        return "\n".join(lines)

    def format_status(self, funds, tick, riders):
        """Return a snapshot of funds, tick and every rider.

        Args:
            funds: Current fund balance.
            tick: Current simulated time.
            riders: Iterable of Rider objects.
        """
        riders = list(riders)
        lines = [f"System status at tick {tick}", f"Funds: {funds}", f"Riders: {len(riders)}"]
        if not riders:
            lines.append("No riders yet. Riders are recruited when funds reach the threshold.")
        for rider in riders:
            col, row = to_cell(rider.position)
            order_ids = [o.id for o in rider.orders]
            lines.append(
                f"  Rider {rider.rider_id}: {STATE_LABELS.get(rider.state, 'unknown')}"
                f" | position ({rider.x}, {rider.y}) grid [{col}, {row}]"
                f" | speed {rider.speed} | orders {order_ids if order_ids else 'none'}"
            )
        return "\n".join(lines)

    def format_orders(self, orders):
        """Return a detailed table of all orders.

        Args:
            orders: Iterable of Order objects.
        """
        orders = list(orders)
        if not orders:
            return "No orders yet."
        lines = []
        for order in orders:
            rider_text = order.rider_id if order.rider_id is not None else "-"
            time_text = order.time_taken if order.time_taken is not None else "-"
            eff_text = order.efficiency if order.efficiency is not None else "-"
            lines.append(
                f"Order #{order.id} [{order.status}] start tick {order.start_tick}"
                f" | restaurant {list(order.res_pos)} | customer {list(order.cus_pos)}"
                f" | distance {order.distance} | time taken {time_text}"
                f" | efficiency {eff_text} | rider {rider_text}"
            )
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """Return every recorded status change for all riders.

        Args:
            riders: Iterable of Rider objects.
        """
        riders = list(riders)
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append(f"Rider {rider.rider_id} log:")
            for entry in rider.log:
                order_text = f"order #{entry['order_id']}" if entry["order_id"] is not None else "no order"
                lines.append(
                    f"  tick {entry['tick']:>5} | {entry['event']:<22}"
                    f" | position ({entry['x']}, {entry['y']})"
                    f" | state {STATE_LABELS.get(entry['state'], 'unknown')}"
                    f" | {order_text}"
                )
        return "\n".join(lines)

    def format_route_map(self, order, rider=None):
        """Render the travelled route as a connected line-segment graph.

        Cell centers are drawn as nodes on a 15x15 canvas; consecutive cells
        are joined by '-' (horizontal) or '|' (vertical) segments.

        Args:
            order: The Order whose trail is drawn.
            rider: Optional Rider assigned to the order (its position is marked 'R').

        Returns:
            Multi-line string.
        """
        width = GRID_DIM * 2 - 1
        canvas = [[" "] * width for _ in range(width)]
        cells = [to_cell(p) for p in order.trail]
        for (ca, ra), (cb, rb) in zip(cells, cells[1:]):
            ax, ay = 2 * ca, 2 * ra
            bx, by = 2 * cb, 2 * rb
            if ra == rb and ca != cb:
                canvas[ay][(ax + bx) // 2] = "-"
            elif ca == cb and ra != rb:
                canvas[(ay + by) // 2][ax] = "|"
        for col, row in cells:
            canvas[2 * row][2 * col] = "*"
        col, row = to_cell(order.res_pos)
        canvas[2 * row][2 * col] = "S"
        col, row = to_cell(order.cus_pos)
        canvas[2 * row][2 * col] = "C"
        if rider is not None:
            col, row = to_cell(rider.position)
            canvas[2 * row][2 * col] = "R"

        lines = [f"Route map for order #{order.id}"]
        lines.append("   " + " ".join(str(c) for c in range(GRID_DIM)).replace(" ", " "))
        for row in range(width):
            label = f"{row // 2:>2} " if row % 2 == 0 else "   "
            lines.append(label + "".join(canvas[row]))
        lines.append("Legend: S restaurant  C customer  R rider  * stop  - | street segment")
        return "\n".join(lines)
