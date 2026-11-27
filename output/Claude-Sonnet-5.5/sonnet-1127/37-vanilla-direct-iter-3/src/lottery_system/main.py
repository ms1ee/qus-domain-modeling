from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("Load list: 1) default 2) custom txt [1]: ").strip()
    if c == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
        if errors:
            for e in errors:
                print(e)
            if input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
                return None
    else:
        users, _ = lm.load_default_list()
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate name removed: {d.name} ({d.department})")
    return valid


def show_groups(lm, users):
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")


def configure_prizes(pm, groups):
    if input("Load default prizes? (y/n) [y]: ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input(
                f"Avoid groups (comma separated, from {list(groups)}): ").split(",") if g.strip()]
            drawer = input("Associated drawer (optional): ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (space separated numbers, Enter to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping original.")
        except ValueError:
            print("Invalid order, keeping original.")


def run_round(prize, lot, rm):
    avoid = ", ".join(prize.avoid_groups) or "none"
    print(f"\n=== {prize.name} | quantity {prize.quantity} | avoid: {avoid} | "
          f"drawer: {prize.associated_drawer or 'n/a'} ===")
    got = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
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
    lot.finish_round(prize, got)
    print("Round results:")
    for u in got:
        print(f"  {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No users loaded.")
        return
    show_groups(lm, users)
    pm = PrizeManager()
    configure_prizes(pm, lm.get_group_info(users).keys())
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in pm.get_prizes():
        run_round(p, lot, rm)
    print("\n=== Final winners ===")
    for n, ws in rm.get_winners_by_prize(pm.get_prizes()).items():
        for w in ws:
            print(f"{n}: {w.user.name} ({w.user.department})")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
