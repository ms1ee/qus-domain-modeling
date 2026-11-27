import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt file > ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        valid, dups = lm.validate_users(users)
        for e in errs:
            print(e)
        for d in dups:
            print(f"Duplicate name: {d.name} ({d.department})")
        if errs or dups:
            a = input("Remove invalid data and continue? (y = continue, n = terminate/reload) ").strip().lower()
            if a != "y":
                if c == "1":
                    continue
                continue
        if not valid:
            print("No valid participants.")
            continue
        return valid


def show_groups(lm, users):
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def configure_prizes(pm, groups):
    pm.load_default_prizes()
    while True:
        print("Prizes:")
        for i, p in enumerate(pm.get_prizes(), 1):
            print(f" {i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
        c = input("a) add prize  v) view groups  o) reorder  s) set avoid groups  d) done > ").strip().lower()
        if c == "a":
            try:
                name = input("Name: ").strip()
                q = int(input("Quantity: "))
                drawer = input("Drawer (blank none): ").strip() or None
                av = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                pm.add_prize(name, q, av, drawer)
            except ValueError as e:
                print("Invalid:", e)
        elif c == "v":
            for g, n in groups.items():
                print(f"  {g}: {n}")
        elif c == "s":
            try:
                i = int(input("Prize number: "))
                av = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                pm.get_prizes()[i - 1].avoid_groups = av
            except (ValueError, IndexError):
                print("Invalid input")
        elif c == "o":
            try:
                order = [int(x) for x in input("New order (e.g. 2 1 3): ").split()]
            except ValueError:
                order = []
            print("Reordered" if pm.reorder_prizes(order) else "Invalid order")
        elif c == "d":
            if pm.get_prizes():
                return


def run_round(lot, rm, prize, idx):
    print(f"\n=== Round {idx}: {prize.name} | quantity {prize.quantity} ===")
    print("Rules:", lot.rule_description(prize))
    winners = []
    paused = False
    while len(winners) < prize.quantity:
        cmd = input("Enter to draw (pause / continue / terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            paused = True
            print("Paused. Type 'continue' to resume.")
            continue
        if cmd == "continue":
            paused = False
            continue
        if paused:
            print("Paused. Type 'continue' to resume.")
            continue
        print(f"Currently drawing winner #{len(winners) + 1}...")
        u = lot.draw_next(prize)
        if u is None:
            print("No eligible participants left.")
            break
        rm.add_winner(u, prize)
        winners.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, winners)
    print("Round results:")
    for i, u in enumerate(winners, 1):
        print(f" {i}. {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    groups = lm.get_group_info(users)
    print("Groups:")
    show_groups(lm, users)
    pm = PrizeManager()
    configure_prizes(pm, groups)
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        run_round(lot, rm, p, i)
    print("\n=== Final winners (high to low prize level) ===")
    ordered = list(reversed(prizes))
    for name, ws in rm.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = rm.export_to_csv(ordered)
    print(msg)


if __name__ == "__main__":
    main()
