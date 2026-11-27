from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("1) default list  2) custom txt file: ").strip()
    if c == "2":
        path = input("Path: ").strip()
        users, errors = lm.load_custom_list(path)
        if errors:
            print("Problems found:")
            for e in errors:
                print("  ", e)
            if input("Terminate upload? (y/N): ").strip().lower() == "y":
                return []
            print("Invalid data removed, continuing.")
        return users
    users, _ = lm.load_default_list()
    return users


def show_groups(lm, users):
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def configure_prizes(pm):
    if input("Load preset prizes? (Y/n): ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/N): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            qty = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
        drawer = input("Associated drawer (optional): ").strip() or None
        try:
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print(e)
    show_prizes(pm)
    s = input("New order by serial numbers (space separated, Enter to keep): ").split()
    if s:
        try:
            ok = pm.reorder_prizes([int(x) for x in s])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, keeping original.")
        show_prizes(pm)


def show_prizes(pm):
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")


def run_round(prize, lot, rm):
    print(f"\n=== {prize.name} | quantity {prize.quantity} ===")
    print(f"Rules: avoid groups {prize.avoid_groups or 'none'}; drawer {prize.associated_drawer or 'n/a'}")
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = input("[Enter]=draw, pause, terminate: ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while True:
                c = input("Paused. Type 'continue' or 'terminate': ").strip().lower()
                if c == "continue":
                    break
                if c == "terminate":
                    cmd = "terminate"
                    break
            if cmd == "terminate":
                print("Round terminated.")
                break
        print(f"Currently drawing the {i}th winner...")
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
    if not users:
        print("No users loaded.")
        return
    show_groups(lm, users)
    pm = PrizeManager()
    configure_prizes(pm)
    prizes = pm.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    lot = LotteryManager(users)
    rm = ResultManager()
    for p in prizes:
        run_round(p, lot, rm)
    print("\n=== Complete winner list ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    if input("Export results? (Y/n): ").strip().lower() != "n":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
