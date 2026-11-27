"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
from config import load_config, save_state
from display import DisplayManager
from input_manager import InputManager, HELP_TEXT
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager, init_system

logger = logging.getLogger("dispatch")


def handle_start(im, args):
    """Handle the 'start' command (order input)."""
    if args:
        coords = im.validate_coordinates(args)
    else:
        coords = im.prompt_coordinates()
        if coords is None:
            print("Order cancelled.")
            return
    order, rider, new_rider = OrderManager.create_order(*coords)
    print("Order #%d created." % order.id)
    print("Restaurant grid center: (%d, %d)  cell %s" % (
        order.res_pos + (PathPlanner.grid_cell(*order.res_pos),)))
    print("Customer   grid center: (%d, %d)  cell %s" % (
        order.cus_pos + (PathPlanner.grid_cell(*order.cus_pos),)))
    print("New rider added: %s" % ("Yes (Rider #%d)" % rider.rider_id
                                    if new_rider and rider else "No"))
    if rider is None:
        print("No rider available; order is pending (funds: %d)." % SystemManager.funds())
        return
    points = rider.remaining_route_points()
    route = PathPlanner.plan_multi(points)
    length = PathPlanner.path_length(points[0], route)
    ticks = PathPlanner.estimate_ticks(length, rider.speed)
    print("Assigned rider: #%d at (%d, %d), speed %d units/tick, queued orders: %d" % (
        rider.rider_id, rider.x, rider.y, rider.speed, len(rider.orders)))
    print("Route length: %d units, estimated time: %d ticks" % (length, ticks))
    print("Route waypoints: %s" % " -> ".join(
        "(%d,%d)" % p for p in [points[0]] + route))
    print(DisplayManager.render_map(riders=[rider], orders=rider.orders,
                                    route_start=points[0], route=route))


def run_command(im, cmd, args):
    """Dispatch one parsed command."""
    if cmd == "start":
        handle_start(im, args)
    elif cmd == "status":
        print(DisplayManager.status_text())
    elif cmd == "orders":
        print(DisplayManager.orders_text())
    elif cmd == "riders":
        print(DisplayManager.riders_text())
    elif cmd == "map":
        print(DisplayManager.render_map())
    elif cmd == "tick":
        n = im.parse_positive_int(args)
        for _ in range(n):
            SystemManager.tick()
        print("Advanced %d tick(s); time is now %d." % (n, SystemManager.current_time()))
    elif cmd == "run":
        n = 0
        while OrderManager.active_orders() and n < 100000:
            SystemManager.tick()
            n += 1
        print("Ran %d tick(s); time is now %d. Active orders: %d" % (
            n, SystemManager.current_time(), len(OrderManager.active_orders())))
    elif cmd == "save":
        path = save_state(args[0] if args else "dispatch_state.json")
        print("State saved to %s" % path)
    elif cmd == "history":
        for i, h in enumerate(im.history, 1):
            print("%3d  %s" % (i, h))
    elif cmd == "help":
        print(HELP_TEXT)
    elif cmd == "quit":
        globalvar.set_value("running", False)
        print("Goodbye.")
    elif cmd == "unknown":
        print("Unknown command '%s'. Type 'help' for a list of commands." % args[0])


def main(argv=None):
    """Program entry point."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default="config.json", help="JSON config file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    init_system(load_config(opts.config))
    im = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running"):
        try:
            line = input("[t=%d] > " % SystemManager.current_time())
        except (EOFError, KeyboardInterrupt):
            print()
            globalvar.set_value("running", False)
            break
        cmd, args = im.parse(line)
        try:
            run_command(im, cmd, args)
        except ValueError as exc:
            print("Invalid input: %s" % exc)
        except Exception as exc:  # graceful recovery
            logger.exception("Unexpected error")
            print("Error: %s (system state recovered)" % exc)
            SystemManager.check_consistency()
        if globalvar.get_value("running"):
            SystemManager.tick()
    return 0


if __name__ == "__main__":
    sys.exit(main())
