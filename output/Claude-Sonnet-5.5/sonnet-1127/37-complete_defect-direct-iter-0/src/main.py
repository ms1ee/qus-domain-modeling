import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("List: 1) default 2) custom txt: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name: {d.name} ({d.department})")
        if (errs or dups):
            a = input("Issues found. 'remove' invalid data and continue, or 'terminate': ").strip()
            if a == "terminate":
                continue
        if valid:
            return valid
        print("No valid users.")


def configure_prizes(pm, groups):
    if input("Load preset prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            drawer = input("Associated drawer (blank for none): ").strip() or None
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(i, p.name, p.quantity, p.avoid_groups, p.associated_drawer)
    o = input("New order (space separated numbers, blank to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def run_round(lot, rm, prize):
    print(f"\n=== {prize.name} x{prize.quantity} ===")
    rule = f"Avoid groups: {prize.avoid_groups or 'none'}; drawer: {prize.associated_drawer or 'none'}"
    print(rule)
    got = []
    for i in range(1, prize.quantity + 1):
        while True:
            cmd = input("Enter to draw (pause/terminate): ").strip().lower()
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            break
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible users left.")
            break
        rm.add_winner(u, prize)
        got.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.record_round(prize, got)


def main():
    lm = ListManager()
    users = load_users(lm)
    info = lm.get_group_info(users)
    for g, c in info.items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    configure_prizes(pm, info)
    prizes = pm.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in prizes:
        run_round(lot, rm, p)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
