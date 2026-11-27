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
        for e in errs:
            print(e)
        if errs and c == "2":
            a = input("Errors found. 'remove' invalid lines and continue, or 'terminate': ").strip()
            if a == "terminate":
                continue
        users, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate removed: {d.name} ({d.department})")
        if users:
            return users
        print("No valid users.")


def configure_prizes(pm, groups):
    if input("Load preset prizes? (y/n) > ").lower().startswith("y"):
        pm.load_default_prizes()
    while input("Add custom prize? (y/n) > ").lower().startswith("y"):
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Lottery person (blank for none): ").strip() or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (space separated numbers, blank to keep) > ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def main():
    lm = ListManager()
    users = load_users(lm)
    groups = lm.get_group_info(users)
    for g, n in groups.items():
        print(f"Group {g}: {n}")
    pm = PrizeManager()
    configure_prizes(pm, groups)
    prizes = pm.get_prizes()
    engine = LotteryManager(users)
    rm = ResultManager()
    for r, prize in enumerate(prizes, 1):
        print(f"\n=== Round {r}: {prize.name}, quantity {prize.quantity} ===")
        print("Rules:", engine.rule_description(prize))
        round_winners = []
        i = 1
        paused = False
        while i <= prize.quantity:
            cmd = input("Enter to draw (pause/continue/terminate) > ").strip().lower()
            if cmd == "pause":
                paused = True
                print("Paused.")
                continue
            if cmd == "continue":
                paused = False
                print("Resumed.")
                continue
            if paused:
                print("Paused; type 'continue'.")
                continue
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing the {i}th winner")
            u = engine.draw_one(prize)
            if u is None:
                print("No eligible participants left.")
                break
            rm.add_winner(u, prize)
            round_winners.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
            i += 1
        engine.record_round(prize, round_winners)
        print("Round results:")
        for k, u in enumerate(round_winners, 1):
            print(f" {k}. {u.name} ({u.department})")
    print("\n=== Final winners ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
