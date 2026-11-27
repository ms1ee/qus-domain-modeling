import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def ask(msg):
    try:
        return input(msg).strip()
    except EOFError:
        return ""


def load_users(lm):
    while True:
        c = ask("Load list: 1) default 2) custom txt > ")
        if c == "2":
            users, errors = lm.load_custom_list(ask("Path: "))
        else:
            users, errors = lm.load_default_list()
        for e in errors:
            print(e)
        if errors and ask("Errors found. Remove invalid data and continue? (y/n) ").lower() != "y":
            print("Upload terminated.")
            if c == "2":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def show_groups(lm, users):
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def setup_prizes(pm):
    if ask("Load default prizes? (y/n) ").lower() == "y":
        pm.load_default_prizes()
    while ask("Add custom prize? (y/n) ").lower() == "y":
        name = ask("Prize name: ")
        try:
            q = int(ask("Quantity: "))
            avoid = [g.strip() for g in ask("Avoid groups (comma separated, optional): ").split(",") if g.strip()]
            drawer = ask("Associated drawer (optional): ") or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = ask("Enter new order as numbers (e.g. 3 1 2), blank to keep: ")
    if o:
        try:
            ok = pm.reorder_prizes([int(x) for x in o.replace(",", " ").split()])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, keeping default.")


def run_round(lot, prize, rm):
    print(f"\n=== {prize.name} | quantity {prize.quantity} ===")
    print("Rules:", lot.describe_rules(prize))
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = ask("Enter to draw, 'pause', or 'terminate': ").lower()
        if cmd == "pause":
            while ask("Paused. Type 'continue': ").lower() not in ("continue",):
                pass
            continue
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing winner #{i}")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        rm.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, won)


def main():
    lm = ListManager()
    users = load_users(lm)
    show_groups(lm, users)
    pm = PrizeManager()
    setup_prizes(pm)
    prizes = pm.get_prizes()
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in prizes:
        run_round(lot, p, rm)
    print("\n=== All Winners ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    if ask("Export results? (y/n) ").lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
