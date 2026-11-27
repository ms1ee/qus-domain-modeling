"""Command line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

from system import init_system, load_config
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager
from path_planner import to_grid_cell

try:  # command history support where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

HELP = """Commands:
  start  (s)  [rx ry cx cy]  create an order (restaurant + customer coords)
  status (st)               show funds, riders and map
  orders (o)                show all orders
  riders (r)                show rider status change logs
  tick   (t)  [n]           advance the simulation n ticks (default 1)
  map    (m)                show the map
  save <file> / load <file> persist / restore state as JSON
  history                   show command history
  help   (h)                show this help
  quit / exit (q)           leave the program
Each command loop iteration advances the simulation by one tick."""


def handle_start(args, system, orders, display, inputs):
    """Process the start command."""
    text = args
    if not text:
        text = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
    coords = inputs.parse_coordinates(text)
    before = len(system.riders)
    order, rider, recruited = orders.create_order(*coords)
    added = len(system.riders) > before
    print("Order #%d created." % order.id)
    print("Restaurant grid: cell (%d,%d) -> point %s" % (
        to_grid_cell(coords[0]), to_grid_cell(coords[1]), order.res_pos))
    print("Customer grid:   cell (%d,%d) -> point %s" % (
        to_grid_cell(coords[2]), to_grid_cell(coords[3]), order.cus_pos))
    print("New rider added: %s%s" % (
        "yes" if added else "no",
        (" (ids %s)" % ", ".join(str(r.rider_id) for r in system.riders[before:]))
        if added else ""))
    print("Funds: %d" % system.funds)
    if rider is None:
        print("No rider available; order remains pending.")
    else:
        print("Assigned to rider %d." % rider.rider_id)
        print(display.render_route(rider, order))


def main(argv=None):
    """Run the interactive command loop."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--load", default=None)
    parser.add_argument("--debug", action="store_true")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    system = init_system(load_config(opts.config))
    if opts.load:
        try:
            system.load_state(opts.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: %s" % exc)
    orders = OrderManager(system)
    display = DisplayManager(system)
    inputs = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")

    while system.running:
        try:
            line = input("[t=%d] > " % system.time)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            cmd, args = inputs.parse_command(line)
            if cmd is None:
                pass
            elif cmd in ("quit", "exit"):
                system.stop()
                break
            elif cmd == "start":
                handle_start(args, system, orders, display, inputs)
            elif cmd == "status":
                print(display.render_status())
            elif cmd == "orders":
                print(display.render_orders())
            elif cmd == "riders":
                print(display.render_rider_logs())
            elif cmd == "map":
                print(display.render_map())
            elif cmd == "tick":
                n = int(args) if args.strip() else 1
                system.tick(max(0, n - 1))
            elif cmd == "save":
                system.save_state(args.strip() or "state.json")
                print("State saved.")
            elif cmd == "load":
                system.load_state(args.strip() or "state.json")
                print("State loaded.")
            elif cmd == "history":
                for i, h in enumerate(inputs.history, 1):
                    print("%3d  %s" % (i, h))
            elif cmd == "help":
                print(HELP)
            else:
                print("Unknown command '%s'. Type 'help'." % cmd)
        except ValueError as exc:
            print("Input error: %s" % exc)
        except OSError as exc:
            print("File error: %s" % exc)
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error")
            print("Error: %s (system state recovered)" % exc)
            system.check_consistency()
        orders.assign_pending()
        system.tick(1)
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
