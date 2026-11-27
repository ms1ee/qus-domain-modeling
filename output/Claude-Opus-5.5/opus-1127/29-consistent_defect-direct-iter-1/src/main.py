"""Command line entry point of the food delivery dispatch simulator."""

import logging
import sys

try:  # command history / arrow keys where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

import globalvar
from display import DisplayManager
from input_manager import InputManager
from system import init_system


def main(argv=None):
    """Run the interactive main loop. Each loop iteration is one tick."""
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    system = init_system("config.json")
    display = DisplayManager()
    inp = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while globalvar.get_value("running", False):
        try:
            line = input("[t=%d] > " % system.time)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd, args = inp.parse(line)
        if cmd == "repeat":
            last = inp.last()
            if not last:
                print("No previous command.")
                continue
            print(last)
            line = last
            cmd, args = inp.parse(line)
        inp.record(line)
        advance = 1
        try:
            if cmd == "":
                pass
            elif cmd == "quit":
                system.stop()
                advance = 0
            elif cmd == "help":
                print(inp.help_text())
                advance = 0
            elif cmd == "start":
                tokens = args
                if not tokens:
                    tokens = input("Enter restaurant_x restaurant_y "
                                   "customer_x customer_y: ").split()
                coords, err = inp.validate_coords(tokens)
                if err:
                    print("Error:", err)
                    advance = 0
                else:
                    result = system.order_manager.create_order(
                        (coords[0], coords[1]), (coords[2], coords[3]))
                    print(display.start_result(result))
            elif cmd == "status":
                print(display.status())
            elif cmd == "orders":
                print(display.orders())
            elif cmd == "riders":
                print(display.riders_log())
            elif cmd == "map":
                print(display.render_map())
            elif cmd == "tick":
                n = 1
                if args:
                    try:
                        n = max(0, int(args[0]))
                    except ValueError:
                        print("Error: tick count must be an integer")
                        n = 0
                system.tick(n)
                advance = 0
                print("Time is now %d" % system.time)
            elif cmd == "run":
                steps = 0
                while not system.all_done() and steps < 100000:
                    system.tick()
                    steps += 1
                advance = 0
                print("Ran %d ticks. Time is now %d" % (steps, system.time))
            elif cmd == "history":
                for i, h in enumerate(inp.history, 1):
                    print("%3d  %s" % (i, h))
                advance = 0
            elif cmd == "save":
                print("Saved to", system.save())
                advance = 0
            else:
                print("Unknown command %r. Type 'help'." % cmd)
                advance = 0
            if advance:
                system.tick(advance)
            problems = system.consistency_check()
            if problems:
                logging.warning("Consistency issues: %s", "; ".join(problems))
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error: %s", exc)
            print("An error occurred; the system state has been preserved.")
    try:
        system.save()
    except OSError as exc:
        logging.warning("Could not save state: %s", exc)
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
