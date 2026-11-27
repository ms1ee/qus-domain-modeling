"""Command line entry point for the food delivery dispatch simulator."""

import logging
import math
import sys

import globalvar
import storage
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager
from path_planner import PathPlanner
from system import init_system

logger = logging.getLogger("dispatch")


class App:
    """Main application tying together all managers."""

    def __init__(self, input_func=input):
        self.system = init_system()
        self.orders = OrderManager(self.system)
        self.display = DisplayManager()
        self.inputs = InputManager(input_func)

    def cmd_start(self, args):
        tokens = list(args)
        if not tokens:
            text = self.inputs.input_func(
                "Enter restaurant_x restaurant_y customer_x customer_y (0-800): ")
            tokens = InputManager.tokenize_coordinates(text)
        else:
            tokens = InputManager.tokenize_coordinates(" ".join(tokens))
        rx, ry, cx, cy = InputManager.validate_coordinates(tokens)
        order = self.orders.create_order(rx, ry, cx, cy)
        rider, new_rider = self.orders.assign_order(order)
        start, waypoints, pick_len, del_len, queued = self.orders.planned_route(rider, order)
        total = pick_len + del_len
        eta = int(math.ceil(total / float(rider.speed))) if total else 0
        out = [
            "Order #%d created." % order.id,
            "Restaurant grid: %s -> center %s" % (order.res_grid, order.res_pos),
            "Customer grid:   %s -> center %s" % (order.cus_grid, order.cus_pos),
            "New rider added: %s" % (
                "Yes (Rider #%d)" % new_rider.rider_id if new_rider else "No"),
            "Assigned to Rider #%d (speed %d units/tick)%s" % (
                rider.rider_id, rider.speed,
                ", queued behind %d order(s)" % queued if queued else ""),
            "Route: %s -> %s" % (start, " -> ".join(str(p) for p in waypoints) or "(here)"),
            "Pickup distance %d, delivery distance %d, total %d units, "
            "estimated time %d tick(s)" % (pick_len, del_len, total, eta),
            self.display.render_map(orders=[order], route=waypoints, route_start=start,
                                    riders=[rider]),
        ]
        if PathPlanner.is_special_case(start, order.res_pos) or \
                PathPlanner.is_special_case(order.res_pos, order.cus_pos):
            out.insert(6, "Note: special case (target directly above/below) - "
                          "sidestep via adjacent street.")
        return "\n".join(out)

    def handle(self, line):
        """Handle one command line. Returns (output, ticks_to_advance)."""
        cmd, args = InputManager.parse(line)
        if cmd == "":
            return "", 1
        if cmd is None:
            return "Unknown command '%s'. Type 'help' for commands." % line.split()[0], 1
        if cmd == "quit":
            self.system.stop()
            path = storage.save_state()
            return "Goodbye!%s" % (" State saved to %s." % path if path else ""), 0
        if cmd == "start":
            return self.cmd_start(args), 1
        if cmd == "status":
            return self.display.show_status(), 1
        if cmd == "orders":
            return self.display.show_orders(), 1
        if cmd == "riders":
            return self.display.show_rider_logs(), 1
        if cmd == "map":
            return self.display.render_map(), 1
        if cmd == "tick":
            n = InputManager.parse_positive_int(args)
            return "Advancing %d tick(s)..." % n, n
        if cmd == "history":
            return "\n".join("%3d  %s" % (i + 1, h)
                             for i, h in enumerate(self.inputs.history)), 1
        if cmd == "save":
            path = storage.save_state()
            return ("State saved to %s." % path) if path else "Save failed.", 1
        if cmd == "help":
            return self.display.show_help(), 1
        return "", 1

    def advance(self, ticks):
        """Advance the simulation, returning formatted events."""
        lines = []
        for _ in range(ticks):
            for ev in self.system.tick():
                lines.append(self.display.format_event(ev))
        return "\n".join(lines)

    def run(self):
        """Main loop: each iteration is one simulation tick."""
        print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
        print(self.display.show_help())
        while self.system.running:
            try:
                line = self.inputs.read_command(
                    "[t=%d funds=%d] > " % (globalvar.get_value("time", 0),
                                           globalvar.get_value("funds", 0)))
            except (EOFError, KeyboardInterrupt):
                print()
                output, _ = self.handle("quit")
                print(output)
                break
            try:
                output, ticks = self.handle(line)
            except ValueError as exc:
                output, ticks = "Error: %s" % exc, 1
            except Exception as exc:  # recovery
                logger.exception("Unexpected error")
                output, ticks = "Unexpected error: %s (system recovered)" % exc, 1
                self.system.check_consistency()
            if output:
                print(output)
            if ticks and self.system.running:
                events = self.advance(ticks)
                if events:
                    print(events)


def main(argv=None):
    """Program entry point."""
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
