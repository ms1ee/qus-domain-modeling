"""Command-line entry point for the food delivery dispatch simulator."""

import logging
import sys

from display import DisplayManager
from input_manager import HELP_TEXT, InputManager
from system import init_system


def run(config_path=None, stream_in=None):
    """Run the interactive main loop. Each loop iteration is one tick."""
    system = init_system(config_path)
    display = DisplayManager(system)
    inputs = InputManager()
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while system.is_running:
        try:
            if stream_in is not None:
                line = stream_in.readline()
                if not line:
                    break
            else:
                line = input("[t=%d] > " % system.current_tick)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            cmd, args = inputs.parse_command(line)
            if cmd == "":
                pass
            elif cmd == "quit":
                system.stop()
                print("Bye.")
                break
            elif cmd == "help":
                print(HELP_TEXT)
            elif cmd == "start":
                if not args:
                    raw = input("Enter restaurant_x restaurant_y customer_x customer_y: ")
                    args = inputs.tokenize(raw)
                coords = inputs.validate_coordinates(args)
                print(display.format_order_result(system.place_order(coords)))
            elif cmd == "status":
                print(display.format_status())
            elif cmd == "orders":
                print(display.format_orders())
            elif cmd == "riders":
                print(display.format_rider_logs())
            elif cmd == "map":
                print(display.render_map())
            elif cmd == "tick":
                n = int(args[0]) if args else 1
                if n < 0:
                    raise ValueError("Tick count must be non-negative")
                system.tick(n - 1 if n > 0 else 0)
                print("Advanced %d tick(s)." % n)
            elif cmd == "history":
                for i, h in enumerate(inputs.command_history, 1):
                    print("%3d  %s" % (i, h))
            elif cmd == "save":
                path = args[0] if args else "dispatch_state.json"
                print("Saved to %s" % system.save_state(path))
            elif cmd == "load":
                path = args[0] if args else "dispatch_state.json"
                system.load_state(path)
                print("Loaded %s" % path)
            else:
                print("Unknown command '%s'. Type 'help'." % cmd)
        except ValueError as exc:
            print("Error: %s" % exc)
        except (OSError, KeyError) as exc:
            print("Error: %s" % exc)
        except Exception as exc:  # graceful recovery
            logging.exception("Unexpected error")
            print("Unexpected error: %s (system recovered)" % exc)
        if system.is_running:
            system.tick(1)
    return 0


def main():
    """Program entry."""
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    return run(config_path)


if __name__ == "__main__":
    sys.exit(main())
