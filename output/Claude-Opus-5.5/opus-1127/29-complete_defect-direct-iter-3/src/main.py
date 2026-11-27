"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import sys

import globalvar
import system
from display import DisplayManager
from input_manager import InputManager
from order import OrderManager


def handle(cmd, args, inp, disp, om):
    """Execute a command. Returns the number of ticks to advance."""
    if cmd == "":
        return 1
    if cmd == "start":
        if not args:
            raw = input("Enter restaurant_x restaurant_y customer_x "
                        "customer_y (0-800): ")
            values = inp.parse_coordinates(raw)
        else:
            values = inp.parse_coordinates(args)
        result = om.create_order(values)
        print(disp.order_result(result))
        return 1
    if cmd == "status":
        print(disp.status())
        return 1
    if cmd == "orders":
        print(disp.orders())
        return 1
    if cmd == "riders":
        print(disp.rider_logs())
        return 1
    if cmd == "map":
        print(disp.current_map())
        return 1
    if cmd == "tick":
        n = inp.parse_tick_count(args)
        print("Advancing %d tick(s)." % n)
        return n
    if cmd == "history":
        for i, h in enumerate(inp.history, 1):
            print("%4d  %s" % (i, h))
        return 1
    if cmd == "save":
        path = system.save_state()
        print("State saved to %s" % path if path else "Save failed.")
        return 1
    if cmd == "help":
        print(disp.help())
        return 0
    if cmd == "quit":
        globalvar.set_value("running", False)
        return 0
    print("Unknown command. Type 'help' for the list of commands.")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level,
                        format="%(levelname)s %(name)s: %(message)s")
    config_path = "config.json"
    if "--config" in argv:
        i = argv.index("--config")
        if i + 1 < len(argv):
            config_path = argv[i + 1]
    system.init_system(config_path)
    inp = InputManager()
    disp = DisplayManager()
    om = OrderManager()
    print("Food Delivery Dispatch Simulator (8x8 grid, 800x800 units)")
    print(disp.help())
    while globalvar.get_value("running", False):
        try:
            line = input("[t=%d funds=%d] > " % (
                globalvar.get_value("time", 0),
                globalvar.get_value("funds", 0)))
        except (EOFError, KeyboardInterrupt):
            print()
            globalvar.set_value("running", False)
            break
        try:
            cmd, args = inp.parse_command(line)
            ticks = handle(cmd, args, inp, disp, om)
            if ticks:
                system.tick(ticks)
        except ValueError as exc:
            print("Input error: %s" % exc)
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
        except Exception as exc:  # recover and keep running
            logging.exception("unexpected error")
            print("Unexpected error: %s (system state recovered)" % exc)
            system.check_consistency()
    path = system.save_state()
    if path:
        print("State saved to %s" % path)
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
