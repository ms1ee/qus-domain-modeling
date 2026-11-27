"""Command-line interaction for the lottery process."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, describe_rule
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

SEPARATOR = "-" * 70


def ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def ask(prompt: str) -> str:
    return input(prompt).strip()


def print_verification_report(errors, duplicates) -> None:
    if errors:
        print("Format errors found:")
        for err in errors:
            print(f"  - {err}")
    if duplicates:
        print("Duplicate names found (later occurrences ignored):")
        for user in duplicates:
            print(f"  - {user.name} ({user.department})")


def print_group_info(info: dict[str, int]) -> None:
    print(SEPARATOR)
    print("Department groups:")
    for dept, count in info.items():
        print(f"  {dept}: {count} people")


def setup_participants(list_mgr: ListManager):
    """Load and verify a participant list. Returns valid users, or None to exit."""
    while True:
        print(SEPARATOR)
        print("Participant list loading")
        print("  1. Load built-in default team building list")
        print("  2. Upload custom txt list (each line: Name,Department or Name;Department)")
        print("  0. Exit")
        choice = ask("Select: ")
        if choice == "0":
            return None
        if choice == "1":
            users, errors = list_mgr.load_default_list()
        elif choice == "2":
            path = ask("Enter txt file path: ")
            users, errors = list_mgr.load_custom_list(path)
        else:
            print("Invalid choice.")
            continue

        valid, duplicates = list_mgr.validate_users(users)
        if errors or duplicates:
            print_verification_report(errors, duplicates)
            while True:
                cmd = ask(
                    "Type 'remove' to drop invalid/duplicate data and continue, "
                    "or 'terminate' to cancel the upload: "
                ).lower()
                if cmd in ("remove", "terminate"):
                    break
                print("Unknown command.")
            if cmd == "terminate":
                print("Upload terminated.")
                continue

        if not valid:
            print("No valid participants found. Please try again.")
            continue
        print(f"Loaded {len(valid)} participants.")
        return valid


def parse_groups(text: str) -> list[str]:
    return [g.strip() for g in text.split(",") if g.strip()]


def print_prizes(prizes) -> None:
    print(SEPARATOR)
    if not prizes:
        print("No prizes configured.")
        return
    print("Prize sequence:")
    for idx, prize in enumerate(prizes, start=1):
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
        drawer = prize.associated_drawer or "none"
        print(f"  {idx}. {prize.name} | quantity: {prize.quantity} | "
              f"avoid groups: {groups} | lottery person: {drawer}")


def add_custom_prize(prize_mgr: PrizeManager, group_names) -> None:
    name = ask("Prize name: ")
    if not name:
        print("Prize name must not be empty.")
        return
    try:
        quantity = int(ask("Quantity: "))
    except ValueError:
        print("Quantity must be an integer.")
        return
    groups = parse_groups(ask("Avoidance groups (comma-separated, blank for none): "))
    for g in groups:
        if g not in group_names:
            print(f"Warning: group '{g}' is not in the participant list.")
    drawer = ask("Associated lottery person (blank for none): ") or None
    try:
        prize_mgr.add_prize(name, quantity, groups, drawer)
        print(f"Prize '{name}' added.")
    except ValueError as exc:
        print(f"Error: {exc}")


def set_avoid_groups(prize_mgr: PrizeManager, group_names) -> None:
    prizes = prize_mgr.get_prizes()
    print_prizes(prizes)
    if not prizes:
        return
    try:
        idx = int(ask("Prize serial number: "))
    except ValueError:
        print("Invalid serial number.")
        return
    if not 1 <= idx <= len(prizes):
        print("Serial number out of range.")
        return
    groups = parse_groups(ask("Avoidance groups (comma-separated, blank for none): "))
    for g in groups:
        if g not in group_names:
            print(f"Warning: group '{g}' is not in the participant list.")
    prizes[idx - 1].avoid_groups = groups
    print("Avoidance groups updated.")


def reorder(prize_mgr: PrizeManager) -> None:
    prizes = prize_mgr.get_prizes()
    print_prizes(prizes)
    if not prizes:
        return
    raw = ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
    try:
        order = [int(x) for x in raw.replace(",", " ").split()]
    except ValueError:
        print("Invalid input. Use integers only.")
        return
    if prize_mgr.reorder_prizes(order):
        print("Prize sequence updated.")
    else:
        print("Invalid order: must contain every serial number exactly once.")


def configure_prizes(prize_mgr: PrizeManager, group_info: dict[str, int]) -> None:
    group_names = set(group_info.keys())
    while True:
        print_prizes(prize_mgr.get_prizes())
        print(SEPARATOR)
        print("Prize configuration")
        print("  1. Load preset prizes")
        print("  2. Add custom prize")
        print("  3. Set avoidance groups for a prize")
        print("  4. Reorder prizes")
        print("  5. View department groups")
        print("  0. Finish configuration")
        choice = ask("Select: ")
        if choice == "1":
            for err in prize_mgr.load_default_prizes():
                print(f"Error: {err}")
        elif choice == "2":
            add_custom_prize(prize_mgr, group_names)
        elif choice == "3":
            set_avoid_groups(prize_mgr, group_names)
        elif choice == "4":
            reorder(prize_mgr)
        elif choice == "5":
            print_group_info(group_info)
        elif choice == "0":
            if prize_mgr.get_prizes():
                return
            print("Please configure at least one prize.")
        else:
            print("Invalid choice.")


def wait_while_paused() -> bool:
    """Block while paused. Returns True to continue, False to terminate the round."""
    print("Lottery paused.")
    while True:
        cmd = ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
        if cmd == "continue":
            print("Lottery resumed.")
            return True
        if cmd == "terminate":
            return False
        print("Unknown command.")


def run_round(index: int, total: int, prize, lottery: LotteryManager, result_mgr: ResultManager) -> None:
    print(SEPARATOR)
    print(f"Round {index}/{total}: {prize.name}")
    print(f"Quantity: {prize.quantity}")
    print(f"Rule: {describe_rule(prize)}")
    if lottery.is_fallback_active(prize):
        print("[Fallback] Cheng Ru Group protection active: pool limited to Cheng Ru Group members.")

    drawn = 0
    terminated = False
    while drawn < prize.quantity:
        print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
        cmd = ask("Press Enter to draw, or type 'pause' / 'terminate': ").lower()
        if cmd == "terminate":
            terminated = True
            break
        if cmd == "pause":
            if not wait_while_paused():
                terminated = True
                break
        elif cmd not in ("", "draw", "continue"):
            print("Unknown command.")
            continue

        user = lottery.draw_one(prize)
        if user is None:
            print("No eligible participants remain for this prize.")
            break
        result_mgr.add_winner(user, prize)
        drawn += 1
        print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

    round_winners = lottery.end_round(prize)
    print(f"Round finished: {len(round_winners)} winner(s)."
          + (" Round was terminated early." if terminated else ""))


def print_summary(result_mgr: ResultManager, prizes) -> None:
    print(SEPARATOR)
    print("Final winner list (by prize level, then winning order):")
    grouped = result_mgr.get_winners_by_prize(prizes)
    for prize_name, winners in grouped.items():
        print(f"\n[{prize_name}]")
        if not winners:
            print("  (no winners)")
        for w in winners:
            print(f"  {w.user.name} | {w.user.department} | {w.prize.name} | "
                  f"{w.winning_time.strftime(ResultManager.TIME_FORMAT)}")


def _run() -> None:
    list_mgr = ListManager()
    users = setup_participants(list_mgr)
    if users is None:
        print("Goodbye.")
        return
    group_info = list_mgr.get_group_info(users)
    print_group_info(group_info)

    prize_mgr = PrizeManager()
    configure_prizes(prize_mgr, group_info)
    prizes = prize_mgr.get_prizes()

    lottery = LotteryManager(users)
    result_mgr = ResultManager()

    print(SEPARATOR)
    print("Lottery starts!")
    for idx, prize in enumerate(prizes, start=1):
        run_round(idx, len(prizes), prize, lottery, result_mgr)

    print_summary(result_mgr, prizes)
    if ask("Export results to awards_result_YYYYMMDD.txt in the current directory? (y/n): ").lower() == "y":
        _, message = result_mgr.export_to_csv(prizes)
        print(message)
    print("Lottery finished. Thank you!")


def main() -> None:
    try:
        _run()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram interrupted. Exiting.")
