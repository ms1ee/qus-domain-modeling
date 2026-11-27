"""Command-line entry point of the Food Delivery Order Dispatch simulator."""

import argparse
import logging
import os
import sys

import globalvar
import persistence
from display import DisplayManager
from input_manager import InputManager
from path_planner import Route
from system import init_system, load_config

HELP_TEXT = """Commands (shortcut in brackets):
  start [rx ry cx cy] (s)  Input a new order (coordinates 0-800)
  status              (st) Show funds and rider states
  orders              (o)  Show all orders
  riders              (r)  Show rider status-change log
  map                 (m)  Show the ASCII map
  step [n]            (n)  Advance the simulation by n ticks
  save [file]              Save state to JSON (default state.json)
  load [file]              Load state from JSON (default state.json)
  history             (hist) Show command history (!! / !n to repeat)
  help                (h)  Show this help
  quit / exit         (q)  Exit
Each command loop iteration advances the simulation by one tick."""


class Application:
    """Main command loop."""

    def __init__(self, config=None):
        self.system = init_system(config)
        self.display = DisplayManager()
        self.input = InputManager()

    def out(self, text=""):
        print(text)

    # ----------------------------------------------------------- commands
    def cmd_start(self, args):
        text = " ".join(args)
        if not text:
            text = input("Enter [restaurant_x, restaurant_y, customer_x, customer_y]: ")
        coords = self.input.parse_coordinates(text)
        order, rider, recruited = self.system.order_manager.create_and_dispatch(coords)
        self.out("Order #{} created.".format(order.id))
        self.out("  Restaurant grid point: ({}, {})".format(*order.res_pos))
        self.out("  Customer grid point:   ({}, {})".format(*order.cus_pos))
        if recruited:
            self.out("  New rider added: yes ({}) - funds now {}".format(
                ", ".join("#{}".format(r.rider_id) for r in recruited), self.system.funds))
        else:
            self.out("  New rider added: no")
        if rider is None:
            self.out("  No rider available (insufficient funds). Order is pending.")
            return
        points = rider.planned_route_points()
        route = Route(points, rider.speed)
        self.out("  Assigned rider: #{} at ({}, {})".format(rider.rider_id, rider.x, rider.y))
        self.out("  Speed: {} units/tick, route length: {} units, estimated time: {} ticks".format(
            rider.speed, route.length, route.estimated_time))
        self.out(self.display.render_map([rider], rider.orders, route_points=points,
                                         highlight_rider=rider))

    def cmd_step(self, args):
        n = self.input.parse_positive_int(args[0] if args else None, 1)
        self.system.advance_tick(n)
        self.out("Advanced {} tick(s). Current tick: {}".format(n, self.system.current_tick))

    def execute(self, cmd, args):
        """Execute a resolved command. Returns False if the tick should not advance."""
        if cmd in ("quit", "exit"):
            self.system.stop()
            self.out("Goodbye.")
            return False
        if cmd == "start":
            self.cmd_start(args)
        elif cmd == "status":
            self.out(self.display.status_text(self.system))
        elif cmd == "orders":
            self.out(self.display.orders_text(self.system.order_manager.all_orders()))
        elif cmd == "riders":
            self.out(self.display.riders_log_text(self.system.riders))
        elif cmd == "map":
            self.out(self.display.render_map(self.system.riders,
                                             self.system.order_manager.all_orders()))
        elif cmd == "step":
            self.cmd_step(args)
        elif cmd == "save":
            path = persistence.save_state(args[0] if args else "state.json")
            self.out("State saved to {}".format(path))
        elif cmd == "load":
            path = args[0] if args else "state.json"
            n_r, n_o = persistence.load_state(path)
            self.out("Loaded {} riders and {} orders from {}".format(n_r, n_o, path))
        elif cmd == "history":
            for i, line in enumerate(self.input.command_history, 1):
                self.out("  {:>3}  {}".format(i, line))
        elif cmd == "help":
            self.out(HELP_TEXT)
        return True

    def run(self):
        """Run the interactive main loop (one iteration = one tick)."""
        self.out("Food Delivery Dispatch Simulator - type 'help' for commands.")
        while self.system.running:
            try:
                line = input("[t={} funds={}]> ".format(self.system.current_tick, self.system.funds))
            except (EOFError, KeyboardInterrupt):
                self.out("")
                self.system.stop()
                break
            try:
                cmd, args = self.input.resolve(line)
                advance = True
                if cmd is not None:
                    advance = self.execute(cmd, args)
                if advance and self.system.running:
                    self.system.advance_tick(1)
            except ValueError as exc:
                self.out("Error: {}".format(exc))
            except (OSError, KeyError) as exc:
                self.out("Error: {}".format(exc))
            except (EOFError, KeyboardInterrupt):
                self.out("\nInput cancelled.")
            except Exception as exc:  # recovery from unexpected errors
                logging.getLogger(__name__).exception("Unexpected error")
                self.out("Unexpected error: {} (system state recovered)".format(exc))
                self.system.consistency_check()


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery order dispatch simulator")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "config.json"))
    parser.add_argument("--load", default=None, help="Load state from a JSON file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = Application(load_config(opts.config))
    if opts.load:
        try:
            persistence.load_state(opts.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: {}".format(exc))
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
