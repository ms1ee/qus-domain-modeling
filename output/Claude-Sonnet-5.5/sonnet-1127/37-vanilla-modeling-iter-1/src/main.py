import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def level_of(name):
    n = name.lower()
    for i, k in enumerate(("first", "second", "third")):
        if k in n:
            return 3 - i
    return 0


def load_users(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt file: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        if errs and c == "2":
            a = input("Errors found. (r)emove invalid lines and continue / (t)erminate: ").lower()
            if a.startswith("t"):
                continue
        users, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name}")
        if users:
            return users
        print("No valid users.")


def setup_prizes(pm, users, lm):
    if input("Load default prizes? (y/n): ").lower().startswith("y"):
        for e in pm.load_default_prizes():
            print(e)
    while input("Add custom prize? (y/n): ").lower().startswith("y"):
        name = input("Name: ").strip()
        try:
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Drawer (optional): ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid input:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (space-separated numbers, Enter to keep): ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping original.")
        except ValueError:
            print("Invalid order, keeping original.")


def main():
    lm = ListManager()
    users = load_users(lm)
    for g, c in lm.get_group_info(users).items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    setup_prizes(pm, users, lm)
    prizes = pm.get_prizes()
    engine = LotteryManager(users)
    rm = ResultManager()

    for r, prize in enumerate(prizes, 1):
        print(f"\n=== Round {r}: {prize.name}, quantity {prize.quantity} ===")
        rule = "Excludes previous winners"
        if prize.associated_drawer == "Li Bin":
            rule += "; avoidance groups not applied (Li Bin)"
        elif prize.avoid_groups:
            rule += "; avoids " + ", ".join(prize.avoid_groups)
        print("Rules:", rule)

        def control(i):
            while True:
                cmd = input(f"Currently drawing winner #{i} (Enter=draw, pause, terminate): ").strip().lower()
                if cmd == "terminate":
                    return "terminate"
                if cmd == "pause":
                    while input("Paused. Type 'continue': ").strip().lower() != "continue":
                        pass
                    continue
                return None

        def on_win(u):
            rm.add_winner(u, prize)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")

        res = engine.draw_round(prize, control, on_win)
        if len(res) < prize.quantity:
            print("Round ended early or pool exhausted.")

    print("\n=== Final Results ===")
    ordered = sorted(prizes, key=lambda p: -level_of(p.name))
    for name, ws in rm.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    ok, msg = rm.export_to_csv(ordered)
    print(msg)


if __name__ == "__main__":
    main()
