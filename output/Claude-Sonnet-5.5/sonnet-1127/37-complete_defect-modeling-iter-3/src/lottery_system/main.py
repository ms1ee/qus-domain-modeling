import sys
import time

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def poll_command():
    try:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            return sys.stdin.readline().strip().lower()
    except Exception:
        pass
    return None


def load_users(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        if errs and c == "2":
            a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
            if a == "t":
                continue
        users, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name} ({d.department})")
        return users


def run_round(idx, prize, lot, results):
    print(f"\n=== Round {idx}: {prize.name} x{prize.quantity} ===")
    rule = f"Avoid groups: {', '.join(prize.avoid_groups) or 'none'}; drawer: {prize.associated_drawer or 'n/a'}"
    print("Rules:", rule)
    print("(type pause / continue / terminate during drawing)")
    won = []
    for i in range(1, prize.quantity + 1):
        cmd = poll_command()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            print("Paused. Type 'continue' to resume or 'terminate'.")
            while True:
                c = input("> ").strip().lower()
                if c in ("continue", "terminate"):
                    cmd = c
                    break
            if cmd == "terminate":
                print("Round terminated.")
                break
        print(f"Currently drawing the {i}th winner...")
        time.sleep(0.3)
        w = lot.draw_one(prize)
        if w is None:
            print("No eligible participants left.")
            break
        won.append(w)
        results.add_winner(w, prize)
        print(f"Congratulations {w.name} ({w.department}) for winning {prize.name}")
    lot.finish_round(prize, won)


def main():
    lmgr = ListManager()
    users = load_users(lmgr)
    print("Groups:")
    for g, c in lmgr.get_group_info(users).items():
        print(f"  {g}: {c}")
    pm = PrizeManager()
    if input("Load preset prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        av = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
        dr = input("Drawer (optional): ").strip() or None
        pm.add_prize(name, q, av, dr)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (e.g. 3 1 2) or Enter to keep: ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")
    lot = LotteryManager(users)
    results = ResultManager()
    for i, p in enumerate(pm.get_prizes(), 1):
        run_round(i, p, lot, results)
    print("\n=== Final winners ===")
    for pname, ws in results.get_winners_by_prize(pm.get_prizes()).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {pname}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(results.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
