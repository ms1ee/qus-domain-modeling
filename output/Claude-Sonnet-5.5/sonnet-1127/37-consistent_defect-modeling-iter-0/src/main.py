import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def rank(prize):
    n = prize.name.lower()
    for i, k in enumerate(("first", "second", "third")):
        if k in n:
            return i
    return 3


def load_users(lm):
    users, errors = [], []
    if input("Load (1) default list or (2) custom txt? [1]: ").strip() == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print("  ", e)
    if errors and input("Errors found. Remove invalid lines and continue? (y/n): ").lower() != "y":
        return []
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name} ({d.department})")
    print("Groups:")
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")
    return users


def configure_prizes(pm):
    if input("Load preset prizes? (y/n) [y]: ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Lottery person: ").strip() or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    ps = pm.get_prizes()
    for i, p in enumerate(ps, 1):
        print(f"{i}. {p.name} x{p.quantity} drawer={p.associated_drawer} avoid={p.avoid_groups}")
    o = input("New order (space separated numbers, blank to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order; kept.")
        except ValueError:
            print("Invalid order; kept.")


def run_round(lot, res, prize, idx):
    print(f"\n=== Round {idx}: {prize.name} x{prize.quantity} (drawer: {prize.associated_drawer}) ===")
    print("Rules:", lot.rule_description(prize))
    winners = []
    for k in range(1, prize.quantity + 1):
        while True:
            cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            break
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing winner #{k}")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants left.")
            break
        winners.append(u)
        res.add_winner(u, prize)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, winners)
    print("Round results:")
    for i, u in enumerate(winners, 1):
        print(f"  {i}. {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No participants. Exiting.")
        return
    pm = PrizeManager()
    configure_prizes(pm)
    prizes = pm.get_prizes()
    lot, res = LotteryManager(users), ResultManager()
    for i, p in enumerate(prizes, 1):
        run_round(lot, res, p, i)
    print("\n=== Final winners ===")
    ordered = sorted(prizes, key=rank)
    for name, ws in res.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department}) {w.time:%H:%M:%S}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(res.export_to_csv(ordered)[1])


if __name__ == "__main__":
    main()
