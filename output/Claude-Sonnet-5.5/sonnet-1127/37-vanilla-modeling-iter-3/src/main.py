import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def setup_list(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt file > ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        if errs:
            a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
            if a == "t":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name}")
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm, groups):
    if input("Load preset prizes? (y/n) ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n) ").strip().lower() == "y":
        name = input("Prize name: ").strip()
        try:
            qty = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        drawer = input("Lottery person (blank for none): ").strip() or None
        print("Groups:", ", ".join(groups))
        av = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
        try:
            pm.add_prize(name, qty, av, drawer)
        except ValueError as e:
            print(e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (e.g. 3 1 2), blank to keep: ").split()
    if o and not pm.reorder_prizes(o):
        print("Invalid order, keeping original.")


def run_round(idx, prize, lot, res):
    print(f"\n=== Round {idx}: {prize.name} | Quantity: {prize.quantity} | "
          f"Drawer: {prize.associated_drawer or '-'} ===")
    print("Rules:", lot.rule_description(prize))
    won = []
    for n in range(1, prize.quantity + 1):
        while True:
            cmd = input("Enter to draw (pause / terminate): ").strip().lower()
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            break
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {n}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants left.")
            break
        res.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, won)


def main():
    lm = ListManager()
    users = setup_list(lm)
    for g, c in lm.get_group_info(users).items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    setup_prizes(pm, list(lm.get_group_info(users)))
    lot = LotteryManager(users)
    res = ResultManager()
    for i, p in enumerate(pm.get_prizes(), 1):
        run_round(i, p, lot, res)
    print("\n=== Final Results ===")
    def level(p):
        n = p.name.lower()
        for k, name in enumerate(("first", "second", "third")):
            if n.startswith(name):
                return k
        return 3
    ordered = sorted(pm.get_prizes(), key=level)
    for name, ws in res.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department})")
    if input("Export results? (y/n) ").strip().lower() == "y":
        print(res.export_to_csv(ordered)[1])


if __name__ == "__main__":
    main()
