import sys
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def main():
    lm = ListManager()
    print("1. Default list  2. Custom txt list")
    if input("> ").strip() == "2":
        users, errs = lm.load_custom_list(input("Path: ").strip())
    else:
        users, errs = lm.load_default_list()
    for e in errs:
        print(e)
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name}")
    for g, c in lm.get_group_info(users).items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    pm.load_default_prizes()
    while input("Add custom prize? (y/N) ").strip().lower() == "y":
        name = input("Name: ").strip()
        qty = int(input("Quantity: "))
        avoid = [g.strip() for g in input("Avoid groups (comma): ").split(",") if g.strip()]
        drawer = input("Drawer: ").strip() or None
        pm.add_prize(name, qty, avoid, drawer)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(i, p.name, p.quantity)
    o = input("New order (space separated, blank to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping default")
        except ValueError:
            print("Invalid order")
    lot = LotteryManager(users)
    rm = ResultManager()
    state = {"paused": False}

    def control():
        return None

    for p in pm.get_prizes():
        print(f"\n== {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
        cmd = input("Enter to start (pause/terminate): ").strip().lower()
        if cmd == "terminate":
            continue
        while cmd == "pause":
            cmd = input("Paused. Type continue: ").strip().lower()
            if cmd == "terminate":
                break
        if cmd == "terminate":
            continue

        def show(i, u, p=p):
            print(f"Currently drawing the {i}th winner")
            rm.add_winner(u, p)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")

        lot.draw_for_prize(p, on_draw=show, control=control)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(pm.get_prizes()).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    ok, msg = rm.export_to_csv(pm.get_prizes())
    print(msg)


if __name__ == "__main__":
    main()
