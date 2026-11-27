from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users():
    lm = ListManager()
    while True:
        c = input("Load list: 1) default 2) custom txt file > ").strip()
        if c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            users, errors = lm.load_default_list()
        for e in errors:
            print(e)
        if errors and input("Errors found. Remove invalid data and continue? (y/n) ").strip().lower() != "y":
            if c == "2":
                print("Upload terminated.")
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name}")
        if not valid:
            print("No valid users.")
            continue
        print("Groups:")
        for g, n in lm.get_group_info(valid).items():
            print(f"  {g}: {n}")
        return valid


def setup_prizes(groups):
    pm = PrizeManager()
    if input("Load preset prizes? (y/n) ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n) ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            qty = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        if qty <= 0 or not name:
            print("Invalid prize")
            continue
        drawer = input("Associated lottery person (blank for none): ").strip() or None
        avoid = [a.strip() for a in input("Avoid groups (comma separated): ").split(",") if a.strip()]
        pm.add_prize(name, qty, avoid, drawer)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity}")
    order = input("New order (e.g. 3 1 2), blank to keep: ").split()
    if order and not pm.reorder_prizes(order):
        print("Invalid order, keeping original.")
    return pm


def run_round(lot, rm, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | rules: {lot.describe_rules(prize)}")
    won = []
    paused = False
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            paused = True
            print("Paused. Type 'continue' to resume.")
            continue
        if paused:
            if cmd == "continue":
                paused = False
                print("Resumed.")
            continue
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants remain.")
            break
        rm.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.record_round(prize, won)
    print("Round results:")
    for n, u in enumerate(won, 1):
        print(f"  {n}. {u.name} ({u.department})")


def main():
    users = load_users()
    pm = setup_prizes(set(u.department for u in users))
    prizes = pm.get_prizes()
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in prizes:
        run_round(lot, rm, p)
    print("\n=== Final winners (high to low prize) ===")
    for name, ws in rm.get_winners_by_prize(list(reversed(prizes))).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    ok, msg = rm.export_to_csv(list(reversed(prizes)))
    print(msg)


if __name__ == "__main__":
    main()
