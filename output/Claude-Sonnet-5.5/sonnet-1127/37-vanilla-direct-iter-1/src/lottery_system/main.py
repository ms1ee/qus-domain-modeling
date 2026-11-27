from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("1) default list  2) custom txt file: ").strip()
    if c == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print("Error:", e)
    if errors and input("Terminate upload? (y/n): ").strip().lower() == "y":
        return []
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name} ({d.department})")
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")
    return users


def config_prizes(pm):
    if input("Load default prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma sep): ").split(",") if g.strip()]
            drawer = input("Associated drawer: ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid input:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (space separated numbers, blank to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping original.")
        except ValueError:
            print("Invalid order, keeping original.")


def run_round(lot, rm, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | drawer {prize.associated_drawer}"
          f" | avoid {prize.avoid_groups or 'none'} ===")
    round_winners = []
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
        print(f"Currently drawing the {i}th winner")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        rm.add_winner(u, prize)
        round_winners.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.record_drawer_result(prize, round_winners)
    print("Round results:", ", ".join(u.name for u in round_winners) or "none")


def main():
    lm, pm, rm = ListManager(), PrizeManager(), ResultManager()
    users = load_users(lm)
    if not users:
        print("No users loaded.")
        return
    config_prizes(pm)
    lot = LotteryManager(users)
    for p in pm.get_prizes():
        run_round(lot, rm, p)
    ordered = list(reversed(pm.get_prizes()))
    print("\n=== Final winners ===")
    for name, ws in rm.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department})")
    print(rm.export_to_csv(ordered)[1])


if __name__ == "__main__":
    main()
