from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users():
    lm = ListManager()
    choice = input("Load list: 1) default  2) custom txt [1]: ").strip()
    if choice == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print(e)
    if errors and input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
        return None
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name}")
    print("Groups:")
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")
    return users


def configure_prizes():
    pm = PrizeManager()
    pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Associated drawer: ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print(f"Invalid: {e}")
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (e.g. 2 1 3) or Enter to keep: ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")
    return pm


def run_round(prize, lot, rm):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | "
          f"avoid: {', '.join(prize.avoid_groups) or 'none'} | "
          f"drawer: {prize.associated_drawer or 'n/a'} ===")
    got = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/terminate): ").strip().lower()
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
    lot.record_round(prize, got)


def main():
    users = load_users()
    if not users:
        print("No users loaded.")
        return
    pm = configure_prizes()
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(p, lot, rm)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
