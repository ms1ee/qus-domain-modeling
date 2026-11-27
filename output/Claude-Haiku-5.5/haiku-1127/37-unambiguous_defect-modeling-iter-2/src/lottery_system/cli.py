"""Command-line interaction for the team building lottery."""

from __future__ import annotations

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, prize_level

BANNER = (
    "=" * 60
    + "\n  Company Team Building - Smart Lottery System\n"
    + "=" * 60
)


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def print_group_info(lm: ListManager, users: list[User]) -> None:
    info = lm.get_group_info(users)
    print("\nDepartment groups:")
    for department, count in info.items():
        print(f"  {department}: {count} member(s)")
    print(f"  Total: {len(users)} participant(s)")


def load_participants(lm: ListManager) -> list[User] | None:
    """Participant list loading with validation. Returns None when user exits."""
    while True:
        print("\nParticipant list loading:")
        print("  1. Load built-in default team building list")
        print("  2. Upload custom txt list (one 'Name,Department' per line)")
        print("  0. Exit")
        choice = ask("Select an option: ")
        if choice == "0":
            return None
        if choice == "1":
            users, errors = lm.load_default_list()
        elif choice == "2":
            path = ask("Enter the txt file path: ")
            users, errors = lm.load_custom_list(path)
        else:
            print("Invalid option.")
            continue

        if errors:
            print(f"\nFound {len(errors)} invalid record(s):")
            for error in errors:
                print(f"  - {error}")
            print("Options: [r] remove invalid records and continue, [a] abort upload")
            if ask("Your choice: ").lower() != "r":
                print("Upload terminated.")
                continue
            print("Invalid records removed.")

        valid, duplicates = lm.validate_users(users)
        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate name(s):")
            for dup in duplicates:
                print(f"  - {dup.name} ({dup.department})")
            print("Options: [r] remove duplicates and continue, [a] abort upload")
            if ask("Your choice: ").lower() != "r":
                print("Upload terminated.")
                continue
            print("Duplicates removed.")

        if not valid:
            print("No valid participants found.")
            continue

        print(f"\nLoaded {len(valid)} valid participant(s).")
        print_group_info(lm, valid)
        return valid


def show_prizes(pm: PrizeManager) -> None:
    prizes = pm.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    print("\nPrize draw order:")
    for pos, prize in enumerate(prizes, start=1):
        avoid = ", ".join(prize.avoid_groups) or "None"
        drawer = prize.associated_drawer or "None"
        print(
            f"  {pos}. {prize.name} | Quantity: {prize.quantity} | "
            f"Avoid groups: {avoid} | Lottery person: {drawer}"
        )


def add_custom_prize(pm: PrizeManager) -> None:
    name = ask("Prize name: ")
    try:
        quantity = int(ask("Quantity: "))
    except ValueError:
        print("Error: quantity must be an integer.")
        return
    groups_text = ask("Avoidance groups (comma-separated, blank for none): ")
    groups = [g.strip() for g in groups_text.split(",") if g.strip()]
    drawer = ask("Associated lottery person (blank for none): ")
    try:
        pm.add_prize(name, quantity, groups, drawer or None)
        print("Prize added.")
    except ValueError as exc:
        print(f"Error: {exc}")


def reorder_prizes(pm: PrizeManager) -> None:
    show_prizes(pm)
    if not pm.get_prizes():
        return
    raw = ask("Enter the new order as serial numbers separated by spaces (e.g. 2 1 3): ")
    try:
        order = [int(token) for token in raw.split()]
    except ValueError:
        print("Invalid input: serial numbers must be integers.")
        return
    if pm.reorder_prizes(order):
        print("Prize order updated.")
        show_prizes(pm)
    else:
        print("Invalid order: every serial number must appear exactly once.")


def set_avoid_groups(pm: PrizeManager) -> None:
    show_prizes(pm)
    prizes = pm.get_prizes()
    if not prizes:
        return
    try:
        pos = int(ask("Enter the serial number of the prize: "))
    except ValueError:
        print("Invalid serial number.")
        return
    if not 1 <= pos <= len(prizes):
        print("Serial number out of range.")
        return
    groups_text = ask("Avoidance groups (comma-separated, blank for none): ")
    groups = [g.strip() for g in groups_text.split(",") if g.strip()]
    if pm.set_avoid_groups(prizes[pos - 1].name, groups):
        print("Avoidance groups updated.")


def manage_prizes(pm: PrizeManager) -> None:
    while True:
        print("\nPrize configuration:")
        print("  1. Load preset prize library")
        print("  2. Add custom prize")
        print("  3. Show prizes (draw order)")
        print("  4. Reorder prizes")
        print("  5. Set avoidance groups for a prize")
        print("  0. Back")
        choice = ask("Select an option: ")
        if choice == "1":
            errors = pm.load_default_prizes()
            if errors:
                for error in errors:
                    print(f"  - {error}")
            else:
                print("Preset prizes loaded.")
        elif choice == "2":
            add_custom_prize(pm)
        elif choice == "3":
            show_prizes(pm)
        elif choice == "4":
            reorder_prizes(pm)
        elif choice == "5":
            set_avoid_groups(pm)
        elif choice == "0":
            return
        else:
            print("Invalid option.")


def wait_while_paused() -> bool:
    """Handle paused state. Returns True if the round should be terminated."""
    print("Lottery paused.")
    while True:
        cmd = ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
        if cmd == "continue":
            print("Lottery resumed.")
            return False
        if cmd == "terminate":
            return True
        print("Unknown command.")


def run_lottery(prizes, lottery: LotteryManager, results: ResultManager) -> None:
    total_rounds = len(prizes)
    for round_no, prize in enumerate(prizes, start=1):
        print(f"\n==== Round {round_no}/{total_rounds}: {prize.name} ====")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        round_winners: list[User] = []
        terminated = False
        while len(round_winners) < prize.quantity and not terminated:
            position = len(round_winners) + 1
            print(f"Currently drawing the {ordinal(position)} winner")
            cmd = ask("Press Enter to draw, or type 'pause' / 'terminate': ").lower()
            if cmd == "terminate":
                terminated = True
            elif cmd == "pause":
                terminated = wait_while_paused()
            elif cmd == "":
                user = lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants remain for this prize. Round ends.")
                    break
                round_winners.append(user)
                results.add_winner(user, prize)
                print(
                    f"*** Congratulations {user.name} ({user.department}) "
                    f"for winning {prize.name}! ***"
                )
            else:
                print("Unknown command. Use Enter, 'pause', or 'terminate'.")

        lottery.finish_round(prize, round_winners)

        print(f"\nRound results for {prize.name}:")
        if round_winners:
            for order, user in enumerate(round_winners, start=1):
                print(f"  {order}. {user.name} ({user.department})")
        else:
            print("  No winners drawn.")
        if terminated:
            print(
                f"Round terminated early: {len(round_winners)} of "
                f"{prize.quantity} winner(s) drawn. Moving to next round."
            )


def print_final_summary(prizes, results: ResultManager) -> None:
    print("\n==== Final Winner List (by prize level, high to low) ====")
    by_prize = results.get_winners_by_prize(prizes)
    if not any(by_prize.values()):
        print("No winners.")
        return
    ordered = sorted(enumerate(prizes), key=lambda t: (prize_level(t[1].name), t[0]))
    for _, prize in ordered:
        winners = by_prize.get(prize.name, [])
        if not winners:
            continue
        print(f"\n{prize.name}:")
        for winner in winners:
            print(
                f"  #{winner.winning_order}  {winner.user.name} "
                f"({winner.user.department})"
            )


def main() -> None:
    print(BANNER)
    lm = ListManager()
    pm = PrizeManager()
    try:
        users = load_participants(lm)
        if users is None:
            print("Goodbye.")
            return

        while True:
            print("\nMain menu:")
            print("  1. View department groups")
            print("  2. Prize configuration")
            print("  3. Start lottery")
            print("  0. Exit")
            choice = ask("Select an option: ")
            if choice == "1":
                print_group_info(lm, users)
            elif choice == "2":
                manage_prizes(pm)
            elif choice == "3":
                prizes = pm.get_prizes()
                if not prizes:
                    print("No prizes configured. Please add prizes first.")
                    continue
                lottery = LotteryManager(users)
                results = ResultManager()
                run_lottery(prizes, lottery, results)
                print_final_summary(prizes, results)
                if ask("\nExport winner list to file? [Y/n]: ").lower() in ("", "y", "yes"):
                    _, message = results.export_to_csv(prizes)
                    print(message)
                print("Lottery finished. Goodbye.")
                return
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Invalid option.")
    except (KeyboardInterrupt, EOFError):
        print("\nProgram interrupted. Exiting.")
