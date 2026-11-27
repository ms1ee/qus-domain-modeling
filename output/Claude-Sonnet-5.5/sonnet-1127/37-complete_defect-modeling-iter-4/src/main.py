import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) Default list  2) Custom txt list: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print("  !", e)
        if errs:
            a = input("Errors found. (r)emove invalid data and continue / (t)erminate: ").strip().lower()
            if a == "t":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"  ! Duplicate name removed: {d.name}")
        if not valid:
            print("No valid users.")
            continue
        print("Groups:")
        for g, n in lm.get_group_info(valid).items():
            print(f"  {g}: {n}")
        return valid


def config_prizes(pm, groups):
    if input("Load preset prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input(f"Avoid groups (comma sep, from {list(groups)}): ").split(",") if g.strip()]
            drawer = input("Drawer (blank for none): ").strip() or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for p in pm.get_prizes():
        pass
    show_prizes(pm)
    o = input("Enter new order as serial numbers (blank keeps): ").replace(",", " ").split()
    if o and not pm.reorder_prizes(o):
        print("Invalid order, keeping default.")


def show_prizes(pm):
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} drawer={p.associated_drawer} avoid={p.avoid_groups}")


def run(lot, pm, rm):
    for r, prize in enumerate(pm.get_prizes(), 1):
        print(f"\n=== Round {r}: {prize.name} | Quantity {prize.quantity} ===")
        print("Rules:", lot.rule_description(prize))
        won = []
        i = 1
        while i <= prize.quantity:
            cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing winner #{i}...")
            u = lot.draw_one(prize)
            if u is None:
                print("No eligible participants left.")
                break
            rm.add_winner(u, prize)
            won.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
            i += 1
        lot.finish_round(prize, won)
        print(f"Round {r} results:")
        for k, u in enumerate(won, 1):
            print(f"  {k}. {u.name} ({u.department})")
    print("\n=== All winners ===")
    grouped = rm.get_winners_by_prize(pm.get_prizes())
    for p, ws in grouped.items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {p}")


def main():
    lm = ListManager()
    users = load_users(lm)
    pm = PrizeManager()
    config_prizes(pm, lm.get_group_info(users).keys())
    if not pm.get_prizes():
        print("No prizes configured.")
        return
    lot = LotteryManager(users)
    rm = ResultManager()
    run(lot, pm, rm)
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
