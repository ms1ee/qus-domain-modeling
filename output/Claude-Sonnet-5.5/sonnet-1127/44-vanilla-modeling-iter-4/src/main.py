"""Beijing Subway fare calculation CLI."""
import argparse
import sys

from data_loader import DATA_FILE_PATH
from data_manager import DataManager
from report import compute_route, format_json, format_text

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def validate_input(dm, text):
    """Return (start, end, error)."""
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, FORMAT_ERR
    s = dm.normalize_station(parts[0])
    if s is None:
        return None, None, "Starting station '%s' does not exist, please check the station name" % parts[0]
    e = dm.normalize_station(parts[1])
    if e is None:
        return None, None, "Ending station '%s' does not exist, please check the station name" % parts[1]
    if s == e:
        return None, None, "Starting station cannot be the same as the ending station"
    return s, e, None


def run_query(dm, args, text):
    s, e, err = validate_input(dm, text)
    if err:
        return None, err
    try:
        r = compute_route(dm, s, e, args.mode, args.max_transfers, args.line_preference)
    except LookupError as ex:
        return None, "Path calculation error: %s" % ex
    except ArithmeticError as ex:
        return None, str(ex)
    except Exception as ex:
        return None, "Path calculation error: %s" % ex
    return (format_json(r) if args.format == "json" else format_text(r)), None


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager(DATA_FILE_PATH)
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        result, err = run_query(dm, args, line)
        if err:
            print(err)
            continue
        print(result)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
