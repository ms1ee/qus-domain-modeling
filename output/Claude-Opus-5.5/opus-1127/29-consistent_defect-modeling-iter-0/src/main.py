"""Command-line entry point for the food delivery dispatch simulator."""

import argparse
import logging
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import persistence
    from system import init_system
    from display import DisplayManager
    from input_manager import InputManager
else:
    from . import persistence
    from .system import init_system
    from .display import DisplayManager
    from .input_manager import InputManager

try:  # command history / line editing where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None


def main(argv=None):
    """Run the interactive main loop. Each iteration is one tick."""
    parser = argparse.ArgumentParser(description="Food delivery dispatch "
                                                 "simulator")
    parser.add_argument("--config", default="config.json",
                        help="JSON configuration file")
    parser.add_argument("--debug", action="store_true", help="debug logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    system = init_system(persistence.load_config(args.config))
    display = DisplayManager(system)
    inputs = InputManager(system, display)
    print("Food Delivery Dispatch Simulator. Type 'help' for commands.")
    while system.running:
        try:
            line = input("[t=%d funds=%d] > " % (system.current_tick,
                                                  system.funds))
        except (EOFError, KeyboardInterrupt):
            print()
            system.stop()
            break
        output, advance = inputs.handle(line)
        if output:
            print(output)
        if system.running and advance:
            system.tick()
    return 0


if __name__ == "__main__":
    sys.exit(main())
