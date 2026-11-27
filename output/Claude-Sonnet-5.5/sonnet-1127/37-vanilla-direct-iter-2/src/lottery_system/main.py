import queue
import threading
import time

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


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
            print("  !", e)
        if errs and c == "2":
            a = input("Errors found. (r)emove invalid lines and continue / (t)erminate: ").strip().lower()
            if a.startswith("t"):
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"  ! Duplicate name removed: {d.name}")
        if valid:
            return valid
        print("No valid users.")


def config_prizes(pm):
    if input("Load default prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            drawer = input("Associated drawer (blank for none): ").strip() or None
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    ps = pm.get_prizes()
    for i, p in enumerate(ps, 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (space-separated numbers, blank to keep): ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order; keeping default.")
        except ValueError:
            print("Invalid order; keeping default.")


def start_reader(q):
    def run():
        try:
            for line in iter(input, None):
                q.put(line.strip().lower())
        except EOFError:
            pass
    threading.Thread(target=run, daemon=True).start()


def run_lottery(users, prizes):
    lot = LotteryManager(users)
    res = ResultManager()
    q = queue.Queue()
    start_reader(q)
    print("Commands during draw: pause / continue / terminate")
    for p in prizes:
        print(f"\n=== {p.name} | quantity {p.quantity} | avoid {p.avoid_groups or 'none'} | drawer {p.associated_drawer or 'none'}")
        drawn = []
        for i in range(1, p.quantity + 1):
            stop = False
            while True:
                try:
                    cmd = q.get_nowait()
                except queue.Empty:
                    break
                if cmd == "terminate":
                    stop = True
                    break
                if cmd == "pause":
                    print("Paused. Type 'continue' to resume.")
                    while True:
                        c2 = q.get()
                        if c2 == "continue":
                            break
                        if c2 == "terminate":
                            stop = True
                            break
                    break
            if stop:
                print("Round terminated.")
                break
            print(f"Currently drawing the {i}th winner...")
            time.sleep(0.5)
            u = lot.draw_one(p)
            if u is None:
                print("No eligible participants remain.")
                break
            drawn.append(u)
            res.add_winner(u, p)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")
        lot.finish_prize(p, drawn)
    return res


def main():
    lm = ListManager()
    users = load_users(lm)
    print("Groups:")
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")
    pm = PrizeManager()
    config_prizes(pm)
    prizes = pm.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    res = run_lottery(users, prizes)
    print("\n=== Final winners (high to low) ===")
    ordered = list(reversed(prizes))
    for name, ws in res.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{w.user.name} ({w.user.department}) - {name}")
    ok, msg = res.export_to_csv(ordered)
    print(msg)


if __name__ == "__main__":
    main()
