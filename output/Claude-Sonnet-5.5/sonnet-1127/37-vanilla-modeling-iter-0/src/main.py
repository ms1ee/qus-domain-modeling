import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("Load list: 1) default 2) custom txt [1]: ").strip()
    if c == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
        for e in errors:
            print(e)
        if errors and input("Continue with valid data? (y/n): ").lower() != "y":
            return []
    else:
        users, _ = lm.load_default_list()
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name}")
    for g, n in lm.get_group_info(valid).items():
        print(f"  {g}: {n}")
    return valid


def setup_prizes(pm):
    pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            av = [g.strip() for g in input("Avoid groups (comma): ").split(",") if g.strip()]
            dr = input("Drawer (blank none): ").strip() or None
            pm.add_prize(name, qty, av, dr)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(i, p.name, p.quantity, p.avoid_groups, p.associated_drawer)
    o = input("New order (e.g. 3 1 2, blank keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, kept.")
        except ValueError:
            print("Invalid order, kept.")


def main():
    users = load_users(ListManager())
    if not users:
        print("No participants.")
        return
    pm = PrizeManager()
    setup_prizes(pm)
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for r, p in enumerate(prizes, 1):
        print(f"\n=== Round {r}: {p.name} x{p.quantity} | avoid: {p.avoid_groups} | drawer: {p.associated_drawer}")
        won = []
        i = 0
        while i < p.quantity:
            cmd = input("Enter to draw (pause/terminate): ").strip().lower()
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing the {i + 1}th winner")
            u = lot.draw_one(p)
            if u is None:
                print("No eligible participants left.")
                break
            rm.add_winner(u, p)
            won.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")
            i += 1
        lot.finish_round(p, won)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
