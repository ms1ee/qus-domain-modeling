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
        users, errors = lm._load_from_path(input("Path: ").strip())
        for e in errors:
            print(e)
        if errors and input("Errors found. Remove invalid lines and continue? (y/n): ").lower() != "y":
            return None
    else:
        users, _ = lm.load_default_list()
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name}")
    print("Groups:", lm.get_group_info(users))
    return users


def configure_prizes(pm, groups):
    if input("Load preset prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma sep): ").split(",") if g.strip()]
            drawer = input("Lottery person: ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (space separated numbers, blank to keep): ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, kept.")
        except ValueError:
            print("Invalid order, kept.")


def run_round(lot, res, prize, idx):
    print(f"\n=== Round {idx}: {prize.name} x{prize.quantity} ===")
    print("Rules:", lot.rule_description(prize))
    got = []
    paused = False
    n = 0
    while n < prize.quantity:
        cmd = input("[Enter]=draw, pause/continue/terminate: ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            paused = True
            print("Paused.")
            continue
        if cmd == "continue":
            paused = False
            continue
        if paused:
            print("Paused. Type 'continue'.")
            continue
        print(f"Currently drawing the {n + 1}th winner")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants left.")
            break
        res.add_winner(u, prize)
        got.append(u)
        n += 1
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, got)
    print("Round results:", [u.name for u in got])


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        return
    pm = PrizeManager()
    configure_prizes(pm, lm.get_group_info(users))
    prizes = pm.get_prizes()
    lot = LotteryManager(users)
    res = ResultManager()
    for i, p in enumerate(prizes, 1):
        run_round(lot, res, p, i)
    print("\n=== Final Winners ===")
    for name, ws in res.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    if input("Export results? (y/n): ").lower() == "y":
        print(res.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
