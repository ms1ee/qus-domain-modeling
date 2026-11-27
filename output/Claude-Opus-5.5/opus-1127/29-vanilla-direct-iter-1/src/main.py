"""Command-line entry point of the food delivery dispatch simulator."""

import logging
import sys

import globalvar
from system import init_system, SystemManager
from order import OrderManager
from display import DisplayManager
from input_manager import InputManager, HELP_TEXT

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

DEFAULT_SAVE = "dispatch_state.json"
MAX_RUN_TICKS = 100000


def advance(n=1):
    """Advance the simulation ``n`` ticks."""
    for _ in range(n):
        SystemManager.tick()
        OrderManager.process_pending()


def handle(cmd, args, inp, out=print):
    """Handle a single command. Returns False when the program should exit."""
    if cmd == "":
        return True
    if cmd == "quit":
        globalvar.set_value("running", False)
        out("Goodbye.")
        return False
    if cmd == "help":
        out(HELP_TEXT)
    elif cmd == "start":
        tokens = args
        if not tokens:
            try:
                tokens = input("Enter restaurant_x restaurant_y customer_x "
                               "customer_y: ")
            except EOFError:
                return True
        coords, err = inp.parse_coordinates(tokens)
        if err:
            out("Error: " + err)
            return True
        result = OrderManager.create_order(coords)
        out(DisplayManager.order_result(result))
    elif cmd == "status":
        out(DisplayManager.status())
    elif cmd == "orders":
        out(DisplayManager.orders())
    elif cmd == "riders":
        out(DisplayManager.riders_log())
    elif cmd == "map":
        out(DisplayManager.render_map())
    elif cmd == "tick":
        n, err = inp.parse_positive_int(args)
        if err:
            out("Error: " + err)
            return True
        advance(n)
        out("Advanced %d tick(s). Time is now %d." % (
            n, globalvar.get_value("time", 0)))
    elif cmd == "run":
        count = 0
        while count < MAX_RUN_TICKS and any(
                o.status != "completed" for o in OrderManager.all_orders()):
            advance(1)
            count += 1
        out("Ran %d tick(s). Time is now %d." % (
            count, globalvar.get_value("time", 0)))
    elif cmd == "history":
        for i, h in enumerate(inp.history, 1):
            out("%4d  %s" % (i, h))
    elif cmd == "save":
        path = args[0] if args else DEFAULT_SAVE
        try:
            SystemManager.save_state(path)
            out("State saved to %s" % path)
        except OSError as exc:
            out("Error saving: %s" % exc)
    elif cmd == "load":
        path = args[0] if args else DEFAULT_SAVE
        try:
            SystemManager.load_state(path)
            out("State loaded from %s" % path)
        except (OSError, ValueError, KeyError) as exc:
            out("Error loading: %s" % exc)
    else:
        out("Unknown command '%s'. Type 'help' for a list." % cmd)
    return True


def main(argv=None):
    """Main loop: each iteration is one simulated tick."""
    argv = sys.argv[1:] if argv is None else argv
    level = logging.DEBUG if "--debug" in argv else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    config = None
    for a in argv:
        if a.startswith("--config="):
            config = a.split("=", 1)[1]
    globalvar._init()
    init_system(config)
    inp = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running", True):
        try:
            line = input("[t=%d] > " % globalvar.get_value("time", 0))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd, args = inp.parse(line)
        try:
            if not handle(cmd, args, inp):
                break
            if cmd not in ("tick", "run", "help", "history", ""):
                advance(1)
            problems = SystemManager.check_consistency()
            for p in problems:
                logging.warning("Consistency issue fixed/detected: %s", p)
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error")
            print("Error: %s (system state preserved)" % exc)
            SystemManager.ensure_initialized()
    return 0


if __name__ == "__main__":
    sys.exit(main())
