from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("Load list: 1) default 2) custom txt file > ").strip()
        if c == "1":
            users, errors = lm.load_default_list()
        elif c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errors:
            print("  !", e)
        if errors:
            a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
            if a != "r":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"  ! Duplicate name removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm, groups):
    pm.load_default_prizes()
    while input("Add custom prize? (y/n) > ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            qty = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        drawer = input("Associated drawer (blank for none): ").strip() or None
        try:
            pm.add_prize(name, qty, drawer and None or None, drawer)
        except ValueError as e:
            print(e)
    print("Groups:", ", ".join(groups))
    for p in pm.get_prizes():
        a = input(f"Avoid groups for '{p.name}' (comma separated, blank none): ").strip()
        if a:
            p.avoid_groups = [g.strip() for g in a.split(",") if g.strip()]
    show_prizes(pm)
    o = input("New order (e.g. 3 1 2), blank keeps: ").strip()
    if o:
        try:
            ok = pm.reorder_prizes([int(x) for x in o.replace(",", " ").split()])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, kept original.")


def show_prizes(pm):
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")


def run_round(lot, prize, rm):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | avoid: "
          f"{', '.join(prize.avoid_groups) or 'none'} | drawer: {prize.associated_drawer or 'none'}")
    got = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/continue/terminate) > ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue' > ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        rm.add_winner(u, prize)
        got.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.record_round(prize, got)
    print("Round results:", "; ".join(f"{u.name} ({u.department})" for u in got) or "none")


def main():
    lm = ListManager()
    users = load_users(lm)
    info = lm.get_group_info(users)
    for g, c in info.items():
        print(f"  {g}: {c}")
    pm = PrizeManager()
    setup_prizes(pm, list(info))
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in pm.get_prizes():
        run_round(lot, p, rm)
    print("\n=== Final winner list ===")
    for name, ws in rm.get_winners_by_prize(pm.get_prizes()).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = rm.export_to_csv(pm.get_prizes())
    print(msg)


if __name__ == "__main__":
    main()
