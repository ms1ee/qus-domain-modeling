"""Command-line interaction for the team building lottery system."""

from __future__ import annotations

import time

from lottery_system.config import LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAW_DELAY_SECONDS = 0.5


# ----- helpers --------------------------------------------------------------
def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _print_header(text: str) -> None:
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def show_group_info(list_mgr: ListManager, users: list[User]) -> None:
    info = list_mgr.get_group_info(users)
    print("Department groups:")
    for group, count in sorted(info.items()):
        print(f"  - {group}: {count} people")


# ----- participant list -------------------------------------------------------
def resolve_problems(valid: list[User]) -> list[User] | None:
    """Ask how to handle format errors / duplicates. Returns None to terminate."""
    print("\nHow do you want to handle the problematic data?")
    print("1. Remove invalid/duplicate data and keep the remaining valid entries")
    print("2. Manually remove specific participants by name")
    print("3. Terminate this upload")
    choice = input("Select option: ").strip()
    if choice == "1":
        return valid
    if choice == "2":
        raw = input("Enter names to remove (comma-separated): ")
        names = {token.strip() for token in raw.split(",") if token.strip()}
        remaining = [user for user in valid if user.name not in names]
        print(f"Removed {len(valid) - len(remaining)} participant(s).")
        return remaining
    if choice == "3":
        return None
    print("Invalid choice. Upload terminated.")
    return None


def setup_user_list(list_mgr: ListManager) -> list[User] | None:
    while True:
        print("\n--- Participant List ---")
        print("1. Load built-in default team building list")
        print("2. Upload custom txt list")
        print("0. Exit")
        choice = input("Select option: ").strip()
        if choice == "0":
            return None
        if choice == "1":
            users, errors = list_mgr.load_default_list()
        elif choice == "2":
            path = input("Enter txt file path: ").strip().strip('"').strip("'")
            users, errors = list_mgr.load_custom_list(path)
        else:
            print("Invalid option.")
            continue

        if errors:
            print("Errors found in the list:")
            for error in errors:
                print(f"  {error}")

        valid, duplicates = list_mgr.validate_users(users)
        if duplicates:
            print("Duplicate names detected (later entries ignored):")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")

        if errors or duplicates:
            resolved = resolve_problems(valid)
            if resolved is None:
                print("Upload terminated.")
                continue
            valid = resolved

        if not valid:
            print("No valid participants available.")
            continue

        print(f"Loaded {len(valid)} participants.")
        show_group_info(list_mgr, valid)
        return valid


# ----- prize configuration ----------------------------------------------------
def show_prizes(prizes: list[Prize]) -> None:
    if not prizes:
        print("No prizes configured.")
        return
    print("Current lottery order:")
    for index, prize in enumerate(prizes, start=1):
        drawer = prize.associated_drawer or "None"
        avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        print(
            f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
            f"Lottery person: {drawer} | Avoided groups: {avoid}"
        )


def add_custom_prize(prize_mgr: PrizeManager, groups: list[str]) -> None:
    name = input("Prize name: ").strip()
    quantity_text = input("Quantity: ").strip()
    if not quantity_text.isdigit() or int(quantity_text) <= 0:
        print("Quantity must be a positive integer.")
        return
    drawer = input("Associated lottery person (blank for none): ").strip() or None

    avoid: list[str] = []
    if groups:
        print("Available groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
    raw = input("Avoidance groups (comma-separated numbers or names, blank for none): ")
    for token in [item.strip() for item in raw.split(",") if item.strip()]:
        if token.isdigit() and 1 <= int(token) <= len(groups):
            avoid.append(groups[int(token) - 1])
        elif token in groups:
            avoid.append(token)
        else:
            print(f"Unknown group ignored: {token}")

    try:
        prize_mgr.add_prize(name, int(quantity_text), avoid, drawer)
        print("Prize added.")
    except ValueError as exc:
        print(f"Cannot add prize: {exc}")


def reorder_prizes_interactive(prize_mgr: PrizeManager) -> None:
    prizes = prize_mgr.get_prizes()
    if not prizes:
        print("No prizes to reorder.")
        return
    show_prizes(prizes)
    print("Enter the new order as serial numbers, e.g. '2 1 3'.")
    raw = input("New order: ")
    tokens = raw.replace(",", " ").split()
    try:
        order = [int(token) for token in tokens]
    except ValueError:
        print("Invalid input: please enter serial numbers only.")
        return
    if prize_mgr.reorder_prizes(order):
        print("Lottery order updated.")
        show_prizes(prize_mgr.get_prizes())
    else:
        print("Invalid order: each serial number must appear exactly once.")


def setup_prizes(prize_mgr: PrizeManager, groups: list[str]) -> None:
    while True:
        print("\n--- Prize Configuration ---")
        print("1. Load preset prizes")
        print("2. Add custom prize")
        print("3. View prizes")
        print("4. Reorder lottery rounds")
        print("0. Finish configuration")
        choice = input("Select option: ").strip()
        if choice == "1":
            errors = prize_mgr.load_default_prizes()
            if errors:
                for error in errors:
                    print(error)
            else:
                print("Preset prizes loaded.")
        elif choice == "2":
            add_custom_prize(prize_mgr, groups)
        elif choice == "3":
            show_prizes(prize_mgr.get_prizes())
        elif choice == "4":
            reorder_prizes_interactive(prize_mgr)
        elif choice == "0":
            if not prize_mgr.get_prizes():
                print("Add at least one prize before starting the lottery.")
                continue
            return
        else:
            print("Invalid option.")


# ----- lottery process --------------------------------------------------------
def describe_rules(prize: Prize, lottery: LotteryManager) -> list[str]:
    lines = ["Rule: previous winners are excluded."]
    if lottery.is_cheng_ru_protection_active(prize):
        lines.append(
            "Fallback (Cheng Ru group protection): only Cheng Ru Group members are "
            "eligible; avoidance groups are overridden."
        )
    elif prize.associated_drawer == LI_BIN:
        lines.append("Special rule (Li Bin): relaxed filtering, avoidance groups ignored.")
    elif prize.avoid_groups:
        lines.append("Avoided groups: " + ", ".join(prize.avoid_groups))
    else:
        lines.append("Avoided groups: none")
    return lines


def await_command(prompt: str) -> str:
    """Wait for operator input. Returns 'next' to proceed or 'terminate' to end the round.
    'pause' suspends the lottery until 'continue' (resume) or 'terminate'."""
    while True:
        command = input(prompt).strip().lower()
        if command == "":
            return "next"
        if command == "terminate":
            return "terminate"
        if command == "pause":
            print("Lottery paused.")
            while True:
                resume = input("Type 'continue' to resume or 'terminate' to end this round: ")
                resume = resume.strip().lower()
                if resume == "continue":
                    print("Lottery resumed.")
                    return "next"
                if resume == "terminate":
                    return "terminate"
                print("Unknown command.")
        print("Unknown command. Use Enter, 'pause', or 'terminate'.")


def run_round(prize: Prize, lottery: LotteryManager, result_mgr: ResultManager) -> list[User]:
    winners: list[User] = []
    for draw_no in range(1, prize.quantity + 1):
        print(f"Currently drawing the {ordinal(draw_no)} winner...")
        time.sleep(DRAW_DELAY_SECONDS)
        user = lottery.draw_one(prize)
        if user is None:
            print("No eligible candidates remain for this prize. Round ends early.")
            break
        result_mgr.add_winner(user, prize)
        winners.append(user)
        print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")
        if draw_no == prize.quantity:
            break
        command = await_command(
            "Press Enter for the next draw, 'pause' to pause, or 'terminate' to end this round: "
        )
        if command == "terminate":
            print("Round terminated by operator.")
            break
    return winners


def print_round_results(prize: Prize, winners: list[User]) -> None:
    print(f"\nRound results for {prize.name} (winning order):")
    if not winners:
        print("  (no winners)")
    for index, user in enumerate(winners, start=1):
        print(f"  {index}. {user.name} ({user.department})")


def run_lottery(prizes: list[Prize], lottery: LotteryManager, result_mgr: ResultManager) -> None:
    total = len(prizes)
    for round_no, prize in enumerate(prizes, start=1):
        _print_header(f"Round {round_no}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Lottery person: {prize.associated_drawer or 'None'}")
        for line in describe_rules(prize, lottery):
            print(line)

        command = await_command(
            "Press Enter to start this round, or type 'terminate' to skip it: "
        )
        if command == "terminate":
            print("Round skipped.")
            continue

        round_winners = run_round(prize, lottery, result_mgr)
        lottery.finish_round(prize, round_winners)
        print_round_results(prize, round_winners)


def show_summary(prizes: list[Prize], result_mgr: ResultManager) -> None:
    _print_header("Final Winner List (by prize level, then winning order)")
    winners_map = result_mgr.get_winners_by_prize(prizes)
    for prize_name, winners in winners_map.items():
        print(f"\n{prize_name}")
        if not winners:
            print("  (no winners)")
        for winner in winners:
            print(
                f"  {winner.sequence}. {winner.user.name} ({winner.user.department}) "
                f"- {prize_name}"
            )


def export_prompt(prizes: list[Prize], result_mgr: ResultManager) -> None:
    choice = input("\nExport the winner list to a file? (y/n): ").strip().lower()
    if choice in ("y", "yes"):
        _, message = result_mgr.export_to_csv(prizes)
        print(message)


# ----- entry point ------------------------------------------------------------
def run() -> None:
    _print_header("Company Team Building Smart Lottery System")
    list_mgr = ListManager()
    users = setup_user_list(list_mgr)
    if users is None:
        print("Goodbye.")
        return

    groups = sorted(list_mgr.get_group_info(users))
    prize_mgr = PrizeManager()
    setup_prizes(prize_mgr, groups)

    prizes = prize_mgr.get_prizes()
    lottery = LotteryManager(users)
    result_mgr = ResultManager()

    print("\nStarting the lottery...")
    run_lottery(prizes, lottery, result_mgr)
    show_summary(prizes, result_mgr)
    export_prompt(prizes, result_mgr)
    print("\nLottery finished. Thank you!")


def main() -> None:
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting the lottery system.")
