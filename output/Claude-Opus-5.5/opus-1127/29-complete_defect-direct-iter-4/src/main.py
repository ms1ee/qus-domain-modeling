"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

import globalvar
from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from order import OrderManager
from system import init_system, load_config

logger = logging.getLogger("dispatch")


def handle_command(cmd, args, sm, om, im, input_func=input):
    """Execute a command; return output text. Sets running False on quit."""
    if cmd == "quit":
        sm.running = False
        return "Goodbye."
    if cmd == "help":
        return HELP_TEXT
    if cmd == "start":
        if args:
            coords = im.parse_coordinates(args)
        else:
            raw = input_func("Enter restaurant_x restaurant_y "
                             "customer_x customer_y: ")
            coords = im.parse_coordinates(raw)
        result = om.create_order(*coords)
        return DisplayManager.start_result_text(result, sm.riders, sm.orders)
    if cmd == "status":
        return DisplayManager.status_text(sm)
    if cmd == "orders":
        return DisplayManager.orders_text(sm.orders)
    if cmd == "riders":
        return DisplayManager.riders_log_text(sm.riders)
    if cmd == "map":
        return DisplayManager.render_map(sm.riders, sm.orders)
    if cmd == "tick":
        n = im.parse_positive_int(args[0] if args else None, 1)
        sm.tick(n)
        return "Advanced %d tick(s). Time is now %d." % (n, sm.time)
    if cmd == "run":
        used = sm.run_until_complete()
        return "Ran %d tick(s). Time is now %d." % (used, sm.time)
    if cmd == "save":
        return "State saved to %s" % sm.save_state(args[0] if args else None)
    if cmd == "load":
        return "State loaded from %s" % sm.load_state(args[0] if args else None)
    if cmd == "history":
        return "\n".join("%3d  %s" % (i + 1, h)
                         for i, h in enumerate(im.history))
    return "Unknown command. Type 'help' for a list of commands."


def main(argv=None):
    """Run the interactive main loop (one tick per command)."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--load", help="JSON state file to load")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    opts = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    sm = init_system(load_config(opts.config))
    om = OrderManager(sm)
    im = InputManager()
    if opts.load:
        try:
            sm.load_state(opts.load)
        except (OSError, ValueError, KeyError) as exc:
            print("Failed to load state: %s" % exc)

    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running", True):
        try:
            line = input("[t=%d] > " % sm.time)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd, args = im.parse_command(line)
        if cmd == "":
            continue
        try:
            out = handle_command(cmd, args, sm, om, im)
            if out:
                print(out)
        except ValueError as exc:
            print("Error: %s" % exc)
        except (OSError, KeyError) as exc:
            print("Error: %s" % exc)
        except Exception as exc:  # graceful recovery
            logger.exception("Unexpected error")
            print("Unexpected error: %s. Recovering state." % exc)
            fixes = sm.consistency_check()
            if fixes:
                print("Repairs: " + "; ".join(fixes))
        if cmd != "quit" and cmd is not None and sm.running:
            try:
                sm.tick(int(sm.config.get("ticks_per_command", 1)))
            except Exception:
                logger.exception("Tick failed")
                sm.consistency_check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
