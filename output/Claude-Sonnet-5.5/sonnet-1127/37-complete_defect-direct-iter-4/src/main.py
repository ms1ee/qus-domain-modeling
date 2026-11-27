import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def poll_command(timeout):
    try:
        import select
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if r:
            return sys.stdin.readline().strip().lower()
    except Exception:
        time.sleep(timeout)
    return None


def load_users(lm):
    while True:
        c = input("Load list: 1) default  2) custom txt file: ").strip()
        if c == "1":
            users, errors = lm.load_default_list()
        elif c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errors:
            print(e)
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name: {d.name} ({d.department})")
        if errors or dups:
            a = input("Remove invalid data and continue? (y/n, n=terminate): ").strip().lower()
            if a != "y":
                if c == "2":
                    continue
                return None
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm, groups):
    if input("Load default prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Prize name: ").strip()
        try:
            qty = int(input("Quantity: ").strip())
            drawer = input("Associated drawer (blank for none): ").strip() or None
            print("Groups:", ", ".join(groups))
            av = input("Avoid groups (comma separated, blank none): ")
            avoid = [g.strip() for g in av.split(",") if g.strip()]
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    if input("Set avoid groups for existing prizes? (y/n): ").strip().lower() == "y":
        for p in pm.get_prizes():
            av = input(f"Avoid groups for '{p.name}' (comma separated): ")
            p.avoid_groups = [g.strip() for g in av.split(",") if g.strip()]
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (e.g. 3 1 2, blank keep): ").replace(",", " ").split()
    if s and not pm.reorder_prizes(s):
        print("Invalid order, keeping original.")


def run_lottery(users, pm, rm):
    lot = LotteryManager(users)
    print("Commands during lottery: pause / continue / terminate")
    for prize in pm.get_prizes():
        print(f"\n=== {prize.name} | quantity {prize.quantity} | "
              f"{lot.rule_description(prize)} ===")
        round_winners = []
        paused = False
        for i in range(1, prize.quantity + 1):
            terminated = False
            while True:
                cmd = poll_command(0.1 if not paused else 0.5)
                if cmd == "pause":
                    paused = True
                    print("Paused. Type 'continue' to resume.")
                elif cmd == "continue":
                    paused = False
                    print("Resumed.")
                elif cmd == "terminate":
                    terminated = True
                    break
                if not paused:
                    break
            if terminated:
                print("Round terminated.")
                break
            print(f"Currently drawing the {i}th winner...")
            u = lot.draw_one(prize)
            if u is None:
                print("No eligible candidates left.")
                break
            rm.add_winner(u, prize)
            round_winners.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
            time.sleep(0.5)
        lot.record_round(prize, round_winners)
        print(f"Round results for {prize.name}:")
        for n, u in enumerate(round_winners, 1):
            print(f"  {n}. {u.name} ({u.department})")


def main():
    lmgr = ListManager()
    users = load_users(lmgr)
    if not users:
        print("Terminated.")
        return
    info = lmgr.get_group_info(users)
    for g, c in info.items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    setup_prizes(pm, list(info))
    if not pm.get_prizes():
        print("No prizes configured.")
        return
    rm = ResultManager()
    run_lottery(users, pm, rm)
    print("\n=== Complete winner list ===")
    for p in pm.get_prizes():
        for w in rm.get_winners_by_prize(pm.get_prizes())[p.name]:
            print(f"{w.user.name},{w.user.department},{w.prize_name}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
