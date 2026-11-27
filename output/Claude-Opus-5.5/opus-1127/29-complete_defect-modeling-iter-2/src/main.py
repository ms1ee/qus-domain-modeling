"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import sys

from config import Configuration
from display import DisplayManager
from input_manager import InputManager
from system import init_system


def handle_command(cmd, args, sm, dm, im):
    """Execute a single command; return text output."""
    if cmd == "":
        return ""
    if cmd == "help":
        return im.help_text()
    if cmd == "quit":
        sm.stop()
        path = sm.save_state()
        return "Goodbye." + (" State saved to %s." % path if path else "")
    if cmd == "start":
        if not args:
            raw = input("Enter restaurant_x restaurant_y customer_x customer_y "
                        "(0-800): ")
            args = raw.split()
        coords = im.validate_coordinates(args)
        result = sm.process_order(coords)
        return dm.show_start_result(result)
    if cmd == "status":
        return dm.show_status(sm)
    if cmd == "orders":
        return dm.show_orders(sm.orders)
    if cmd == "riders":
        return dm.show_rider_logs(sm.riders)
    if cmd == "map":
        return dm.render_map(sm.riders, sm.orders)
    if cmd == "tick":
        n = im.validate_positive_int(args, 1)
        sm.tick(n)
        return "Advanced %d tick(s). Now t=%d." % (n, sm.current_tick)
    if cmd == "run":
        n = sm.run_until_idle()
        return "Advanced %d tick(s). Now t=%d." % (n, sm.current_tick)
    if cmd == "history":
        return "\n".join("%d: %s" % (i + 1, c)
                         for i, c in enumerate(im.command_history))
    if cmd == "save":
        path = sm.save_state()
        return "Saved to %s" % path if path else "Save failed."
    return "Unknown command."


def main(argv=None):
    """Run the interactive main loop (each iteration = one tick)."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch")
    parser.add_argument("--config", default=None, help="JSON config file")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    sm = init_system(Configuration(args.config))
    dm = DisplayManager()
    im = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while sm.running:
        try:
            line = input("dispatch[t=%d]> " % sm.current_tick)
        except (EOFError, KeyboardInterrupt):
            print()
            print(handle_command("quit", [], sm, dm, im))
            break
        try:
            cmd, cargs = im.parse(line)
            out = handle_command(cmd, cargs, sm, dm, im)
            if out:
                print(out)
        except (EOFError, KeyboardInterrupt):
            print("\nInput cancelled.")
        except ValueError as exc:
            print("Error: %s" % exc)
        except Exception as exc:  # recover gracefully
            logging.getLogger(__name__).exception("Unexpected error")
            print("Unexpected error: %s (state recovered)" % exc)
            sm.check_consistency()
        if sm.running:
            sm.tick()
    return 0


if __name__ == "__main__":
    sys.exit(main())
