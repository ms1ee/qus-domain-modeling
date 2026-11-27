"""Entry point of the Beijing Subway fare calculation system.

Usage examples::

    python src/main.py
    python src/main.py --mode least_transfer --format json
    python src/main.py --line_preference "Line 1" --output_file result.txt
    python src/main.py --check_data
"""

import sys

from cli import SubwayCLI, parse_args
from data_loader import DataLoadError, load_subway_data
from integrity import check_integrity, format_integrity_report
from network import SubwayNetwork


def main(argv=None):
    """Run the application and return the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data()
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    network = SubwayNetwork(data)

    if args.check_data:
        report = check_integrity(network)
        print(format_integrity_report(report))
        return 0 if report.passed else 1

    return SubwayCLI(network, args).run()


if __name__ == "__main__":
    sys.exit(main())
