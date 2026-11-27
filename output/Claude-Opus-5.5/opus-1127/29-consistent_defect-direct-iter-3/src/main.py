"""Command line entry point for the food delivery dispatch simulator."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import globalvar  # noqa: E402
import persistence  # noqa: E402
import system  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager  # noqa: E402
from order import OrderManager  # noqa: E402

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"


def handle_start(args, inputs):
    if args:
        raw = " ".join(args)
    else:
        raw = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
    try:
        coords = inputs.parse_coordinates(raw)
    except ValueError as exc:
        print("Invalid input: {}".format(exc))
        return
    order, rider, new_rider = OrderManager.create_order(coords)
    print("Order {} created.".format(order.id))
    print("Restaurant grid: ({}, {})  Customer grid: ({}, {})".format(
        order.res_pos[0], order.res_pos[1], order.cus_pos[0], order.cus_pos[1]))
    print("New rider added: {}".format("yes" if new_rider else "no"))
    if rider is None:
        print("No rider available (insufficient funds); order is pending.")
        return
    print("Assigned to rider {}".format(rider.rider_id))
    print(DisplayManager.format_route(rider))


def execute(cmd, args, inputs, manager):
    """Execute a parsed command. Returns False when the loop should stop."""
    if cmd == "start":
        handle_start(args, inputs)
    elif cmd == "status":
        print(DisplayManager.format_status(manager.funds, manager.riders,
                                           manager.current_time))
        problems = system.check_consistency()
        for p in problems:
            print("WARNING: " + p)
    elif cmd == "orders":
        print(DisplayManager.format_orders(manager.orders))
    elif cmd == "riders":
        print(DisplayManager.format_rider_logs(manager.riders))
    elif cmd == "map":
        print(DisplayManager.render_map(manager.riders, manager.orders))
    elif cmd == "tick":
        n = 1
        if args:
            try:
                n = max(1, int(args[0]))
            except ValueError:
                print("tick expects an integer")
                return True
        manager.tick(n - 1)  # the loop itself advances one tick
        print("Advancing {} tick(s).".format(n))
    elif cmd == "save":
        path = args[0] if args else STATE_FILE
        persistence.save_state(path)
        print("State saved to {}".format(path))
    elif cmd == "load":
        path = args[0] if args else STATE_FILE
        try:
            persistence.load_state(path)
            print("State loaded from {}".format(path))
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: {}".format(exc))
    elif cmd == "history":
        for i, line in enumerate(inputs.history, 1):
            print("{:>4}  {}".format(i, line))
    elif cmd == "help":
        print(inputs.help_text())
    elif cmd == "quit":
        manager.stop()
        return False
    return True


def main():
    logging.basicConfig(level=os.environ.get("DISPATCH_LOG", "WARNING"),
                        format="%(levelname)s %(name)s: %(message)s")
    system.init_system()
    try:
        persistence.load_config(CONFIG_FILE)
    except (OSError, ValueError) as exc:
        print("Config ignored: {}".format(exc))
    manager = system.SystemManager()
    inputs = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running", True):
        try:
            line = input("[t={}] > ".format(manager.current_time))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd, args = inputs.parse_command(line)
        if cmd is None:
            print("Unknown command. Type 'help' for the command list.")
        elif cmd:
            try:
                if not execute(cmd, args, inputs, manager):
                    break
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception as exc:  # graceful recovery
                logging.exception("Command failed")
                print("Error: {}. System state preserved.".format(exc))
        manager.tick(1)
        OrderManager.assign_pending()
    print("Goodbye.")


if __name__ == "__main__":
    main()
