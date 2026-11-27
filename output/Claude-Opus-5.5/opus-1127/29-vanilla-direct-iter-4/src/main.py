"""Command-line entry point of the food delivery dispatch simulator.

Run with:  python src/main.py [--config FILE] [--load FILE] [--debug]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
import globalvar  # noqa: E402
from display import DisplayManager  # noqa: E402
from input_manager import InputManager, InputError, HELP_TEXT  # noqa: E402
from system import init_system  # noqa: E402

logger = logging.getLogger("dispatch")


def handle_command(system, im, dm, cmd, args, read=input):
    """Execute one command; returns the text to print."""
    if cmd == "start":
        if not args:
            raw = read("Enter restaurant_x restaurant_y customer_x customer_y: ")
            args = raw.replace(",", " ").replace("[", " ").replace("]", " ").split()
        coords = im.validate_coordinates(args)
        result = system.order_manager.dispatch(coords)
        return dm.format_dispatch(result)
    if cmd == "status":
        return dm.format_status(system)
    if cmd == "orders":
        return dm.format_orders(system.order_manager.all_orders())
    if cmd == "riders":
        return dm.format_rider_logs(system.riders)
    if cmd == "map":
        routes = [r.planned_route() for r in system.riders if r.orders]
        return dm.render_map(system.riders, system.order_manager.all_orders(),
                             routes)
    if cmd == "tick":
        n = im.parse_positive_int(args, 1)
        done = system.tick(n)
        msg = "Advanced %d tick(s). Time is now %d." % (n, system.time)
        if done:
            msg += " Delivered orders: %s" % [o.id for o in done]
        return msg
    if cmd == "run":
        ticks = system.run_until_idle()
        return "Ran %d tick(s). Time is now %d.\n%s" % (
            ticks, system.time, dm.format_status(system))
    if cmd == "save":
        return "State saved to %s" % system.save(args[0] if args else None)
    if cmd == "load":
        return "State loaded from %s" % system.load(args[0] if args else None)
    if cmd == "history":
        return im.format_history()
    if cmd == "help":
        return HELP_TEXT
    if cmd == "quit":
        system.stop()
        return "Goodbye."
    raise InputError("Unknown command '%s'. Type 'help' for commands." % cmd)


def main(argv=None):
    """Run the interactive main loop."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--load", help="load a saved JSON state file")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    opts = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    system = init_system(opts.config)
    if opts.load:
        try:
            system.load(opts.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Could not load state: %s" % exc)

    im = InputManager(0, int(config.get("map_size")))
    dm = DisplayManager()
    print("Food Delivery Dispatch System - funds %d. Type 'help' for commands."
          % system.funds)

    while globalvar.get_value("running", False):
        try:
            line = input("dispatch> ")
        except (EOFError, KeyboardInterrupt):
            print()
            system.stop()
            break
        try:
            cmd, args = im.parse(line)
            if not cmd:
                continue
            output = handle_command(system, im, dm, cmd, args)
            print(output)
            if cmd not in ("quit", "help", "history"):
                system.tick(int(config.get("ticks_per_command")))
        except InputError as exc:
            print("Error: %s" % exc)
        except (EOFError, KeyboardInterrupt):
            print("\nInput cancelled.")
        except Exception as exc:  # graceful recovery
            logger.exception("Unexpected error")
            print("Unexpected error: %s (system state checked and recovered)" % exc)
            system.check_consistency()
    return 0


if __name__ == "__main__":
    sys.exit(main())
