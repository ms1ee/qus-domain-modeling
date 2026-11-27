"""Command-line entry point of the Food Delivery Order Dispatch System."""

import argparse
import logging
import sys

import globalvar
from input_manager import InputError
from system import init_system

try:  # enables arrow-key command history where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

HELP = """Commands (shortcut in brackets):
  start [n|1] rx ry cx cy  Create an order (coords 0-800); prompts if omitted
  status [s|2]             Funds and rider states
  orders [o|3]             All orders
  riders [r|4]             Rider status-change history
  map [m|5]                ASCII map of riders and active orders
  tick [t|6] [N]           Advance simulation N ticks (default 1)
  history [h]              Command history (!! repeat last, !n repeat n-th)
  save [file]              Save system data to JSON
  check                    Run a state consistency check
  help [?]                 This help
  quit / exit [q]          Exit
Every command iteration advances the simulation by one tick."""


def handle(sm, cmd, args):
    """Execute a command; returns True if an automatic tick should follow."""
    dm, im = sm.display_manager, sm.input_manager
    if cmd == "start":
        if not args:
            args = im.read_line("Enter restaurant_x restaurant_y customer_x customer_y: ")
        result = sm.submit_order(args)
        print(dm.format_order_result(result))
    elif cmd == "status":
        print(dm.format_status(sm.funds, sm.current_time, sm.riders))
    elif cmd == "orders":
        print(dm.format_orders(sm.orders))
    elif cmd == "riders":
        print(dm.format_rider_logs(sm.riders))
    elif cmd == "map":
        print(dm.format_map(sm.riders, sm.orders))
    elif cmd == "tick":
        n = 1
        if args:
            try:
                n = int(args[0])
            except ValueError:
                raise InputError("Tick count must be an integer.")
            if not 1 <= n <= 10000:
                raise InputError("Tick count must be between 1 and 10000.")
        sm.tick(n)
        print("Advanced %d tick(s); time is now %d." % (n, sm.current_time))
        return False
    elif cmd == "history":
        for i, c in enumerate(im.command_history, 1):
            print("%4d  %s" % (i, c))
    elif cmd == "save":
        path = args[0] if args else None
        sm.save_data(path)
        print("Data saved to %s." % (path or sm.config.get("data_file")))
    elif cmd == "check":
        fixes = sm.check_consistency()
        print("\n".join(fixes) if fixes else "System state is consistent.")
    elif cmd == "help":
        print(HELP)
    elif cmd == "quit":
        sm.stop()
        return False
    return True


def main(argv=None):
    """Run the interactive dispatch simulator."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--no-save", action="store_true", help="do not save data on exit")
    opts = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if opts.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    sm = init_system(opts.config)
    im = sm.input_manager
    print("Food Delivery Order Dispatch System - 8x8 grid (800x800 units)")
    print("Type 'help' for commands.")
    while globalvar.get_value("running"):
        raw = im.read_line("[t=%d funds=%d] dispatch> " % (sm.current_time, sm.funds))
        try:
            cmd, args = im.parse(raw)
            if cmd == "":
                auto_tick = True
            elif cmd is None:
                print("Unknown command. Type 'help' for the list of commands.")
                auto_tick = False
            else:
                auto_tick = handle(sm, cmd, args)
            if auto_tick:
                sm.tick(1)
        except InputError as exc:
            print("Input error: %s" % exc)
        except Exception as exc:  # graceful recovery
            logging.getLogger("dispatch").exception("Unexpected error")
            print("Error: %s. Recovering system state..." % exc)
            for fix in sm.check_consistency():
                print("  " + fix)

    if not opts.no_save:
        try:
            sm.save_data()
            print("Data saved to %s." % sm.config.get("data_file"))
        except OSError as exc:
            print("Could not save data: %s" % exc)
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
