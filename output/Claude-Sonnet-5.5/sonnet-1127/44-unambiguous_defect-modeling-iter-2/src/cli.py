"""Command-line interface."""
import argparse
import sys

from data_manager import DataManager
from validator import InputValidator, ValidationError
from pathfinding import ShortestPath, PathfindingConfig, MODES, SHORTEST_DISTANCE
from fare_calculator import Sum_money, calculate_estimated_time
from report import build_summary, render


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default=SHORTEST_DISTANCE)
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--query", default=None, help="single query 'Start; End' (non-interactive)")
    return p.parse_args(argv)


def run_query(dm, start, end, args):
    names = dm.number_to_station
    pref = [args.line_preference] if args.line_preference else []
    cfg = PathfindingConfig(args.mode, args.max_transfers, pref)
    s, t = dm.station_to_number[start], dm.station_to_number[end]
    try:
        sp = ShortestPath(dm.graph, s, cfg)
        note = ""
        if not sp.has_path_to(t) and args.max_transfers is not None:
            sp = ShortestPath(dm.graph, s, PathfindingConfig(args.mode, None, pref))
            note = "Note: no route within the transfer limit; showing best route without limit.\n"
        if not sp.has_path_to(t):
            raise ValueError("no route found")
        nodes, edges = sp.path_with_edges(t)
        dist = sp.dist_to[t]
        transfers = sp.get_transfer_count(t)
    except Exception as e:
        return f"Path calculation failed: {e}"
    try:
        fare = Sum_money(dist)
        minutes = calculate_estimated_time(dist, transfers)
    except Exception as e:
        return f"Fare calculation failed: {e}"
    summary = build_summary(start, end, args.mode, [names[n] for n in nodes], edges,
                            names, dist, fare, minutes)
    text = render(summary, args.format)
    return note + text if args.format == "text" else text


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print(f"Failed to load data: {e}")
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    validator = InputValidator(dm)
    first = [True]

    def emit(text):
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "w" if first[0] else "a", encoding="utf-8") as f:
                    f.write(text + "\n")
                first[0] = False
            except OSError as e:
                print(f"Cannot write output file: {e}")

    if args.query is not None:
        try:
            st, en = validator.parse(args.query)
        except ValidationError as e:
            print(e)
            return 1
        emit(run_query(dm, st, en, args))
        return 0

    print("Beijing Subway fare query. Enter 'Start; End', or 'q' to quit.")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        try:
            st, en = validator.parse(line)
        except ValidationError as e:
            print(e)
            continue
        emit(run_query(dm, st, en, args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
