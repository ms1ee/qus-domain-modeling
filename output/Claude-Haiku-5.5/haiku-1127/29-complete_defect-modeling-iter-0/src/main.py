"""Entry point of the Food Delivery Order Dispatch System.

Run with: ``python src/main.py [--config config.json] [--log-level INFO]``
"""

import argparse
import logging
import sys

import system
from input_manager import InputManager

logger = logging.getLogger("dispatch")


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional list of arguments (defaults to ``sys.argv[1:]``).

    Returns:
        argparse.Namespace with ``config``, ``log_level`` and ``log_file``.
    """
    parser = argparse.ArgumentParser(description="Food delivery dispatch simulator")
    parser.add_argument("--config", default=None, help="path to a JSON configuration file")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging verbosity",
    )
    parser.add_argument("--log-file", default=None, help="write logs to this file")
    return parser.parse_args(argv)


def configure_logging(level, log_file=None):
    """Configure the root logger.

    Args:
        level: Logging level name.
        log_file: Optional file path; logs go to stderr when omitted.
    """
    if log_file:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stderr)
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler],
    )


def main(argv=None):
    """Program entry point.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    configure_logging(args.log_level, args.log_file)
    try:
        system.init_system(args.config)
        manager = system.SystemManager()
        InputManager(manager).run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        return 130
    except Exception:
        logger.exception("Fatal error")
        print("A fatal error occurred. See the log for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
