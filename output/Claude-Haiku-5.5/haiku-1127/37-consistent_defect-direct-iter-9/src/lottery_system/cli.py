"""Command-line interface for the team building smart lottery system."""

from __future__ import annotations

import re
from typing import Optional

from lottery_system.constants import (
    CHEN_QIXIAN,
    JIN_DUO,
    KNOWN_DRAWERS,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import (
    ResultManager,
    Winner,
    sort_prizes_by_level,
)


class AppState:
    """Holds the session state of the running program."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: Optional[LotteryManager] = None
        self.results = ResultManager()

    def set_users(self, users: list[User]) -> None:
        self.users = list(users)
        self.reset_lottery()

    def reset_lottery(self) -> None:
        self.lottery = None
        self.results = ResultManager()


# ----- input helpers ---------------------------------------------------------
def _ask(prompt: str) -> str:
    return input(prompt).strip()


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _group_names(state: AppState) -> list[str]:
    return list(state.list_manager.get_group_info(state.users).keys())


# ----- list menus ------------------------------------------------------------
def menu_load_default(state: AppState) -> None:
    users, errors = state.list_manager.load_default_list()
    for err in errors:
        print(err)
    state.set_users(users)
    print(f"Loaded default team building list: {len(users)} participants.")


def menu_upload_custom(state: AppState) -> None:
    path = _ask("Enter path of the txt list (blank to cancel): ")
    if not path:
        print("Upload cancelled.")
        return

    users, errors = state.list_manager.load_custom_list(path)
    valid, duplicates = state.list_manager.validate_users(users)

    if errors:
        print("Invalid entries (will be ignored):")
        for err in errors:
            print(f"  {err}")
    if duplicates:
        print("Duplicate names (only first occurrence kept):")
        for user in duplicates:
            print(f"  {user.name} ({user.department})")

    if errors or duplicates:
        choice = _ask(
            "[c] continue with valid entries / [r] remove entries manually / "
            "[q] terminate upload: "
        ).lower()
        if choice == "q":
            print("Upload terminated. Current list unchanged.")
            return
        if choice == "r":
            valid = _manual_remove(valid)
        elif choice != "c":
            print("Unknown option. Upload terminated.")
            return

    if not valid:
        print("No valid entries remain. Upload failed.")
        return

    state.set_users(valid)
    print(f"Loaded custom list: {len(valid)} participants.")
    _print_group_info(state.list_manager.get_group_info(valid))


def _manual_remove(users: list[User]) -> list[User]:
    current = list(users)
    while current:
        print("Current valid entries:")
        for i, user in enumerate(current, 1):
            print(f"  {i}. {user.name} ({user.department})")
        raw = _ask("Enter numbers to remove (comma separated), or blank to finish: ")
        if not raw:
            break
        to_remove: set[int] = set()
        for token in re.split(r"[,\s]+", raw):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(current):
                to_remove.add(int(token) - 1)
            else:
                print(f"Ignored invalid number: {token}")
        current = [u for i, u in enumerate(current) if i not in to_remove]
    return current


def menu_groups(state: AppState) -> None:
    if not state.users:
        print("No participant list loaded.")
        return
    _print_group_info(state.list_manager.get_group_info(state.users))


def _print_group_info(info: dict[str, int]) -> None:
    print("Department groups:")
    for dept, count in info.items():
        print(f"  {dept}: {count} people")
    print(f"  Total groups: {len(info)}")


# ----- prize menus -----------------------------------------------------------
def menu_prizes(state: AppState) -> None:
    while True:
        print("\n--- Prize Configuration ---")
        print("1. Load default prize library")
        print("2. Add custom prize")
        print("3. View prizes")
        print("4. Set lottery order")
        print("5. Edit avoidance groups of a prize")
        print("0. Back")
        choice = _ask("Select: ")
        if choice == "1":
            errors = state.prize_manager.load_default_prizes()
            for err in errors:
                print(err)
            print("Default prize library loaded.")
        elif choice == "2":
            _add_custom_prize(state)
        elif choice == "3":
            _print_prizes(state.prize_manager.get_prizes())
        elif choice == "4":
            _reorder_prizes(state)
        elif choice == "5":
            _edit_prize_groups(state)
        elif choice == "0":
            return
        else:
            print("Invalid option.")


def _print_prizes(prizes: list[Prize]) -> None:
    if not prizes:
        print("No prizes configured.")
        return
    print("Prizes (lottery order):")
    for i, prize in enumerate(prizes, 1):
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
        drawer = prize.associated_drawer or "none"
        print(f"  {i}. {prize.name} | quantity: {prize.quantity} | "
              f"avoid groups: {groups} | lottery person: {drawer}")


def _choose_groups(state: AppState, existing: Optional[list[str]] = None) -> list[str]:
    known = _group_names(state)
    if known:
        print("Available department groups:")
        for i, group in enumerate(known, 1):
            print(f"  {i}. {group}")
    raw = _ask("Avoidance groups (numbers or names, comma separated; blank for none): ")
    if not raw:
        return []
    selected: list[str] = []
    for token in re.split(r"[,\uff0c]", raw):
        token = token.strip()
        if not token:
            continue
        if token.isdigit() and known:
            idx = int(token) - 1
            if 0 <= idx < len(known):
                selected.append(known[idx])
            else:
                print(f"Ignored invalid group number: {token}")
        elif known and token not in known:
            print(f"Ignored unknown group: {token}")
        else:
            selected.append(token)
    return list(dict.fromkeys(selected))


def _choose_drawer() -> Optional[str]:
    print("Lottery person options: " + ", ".join(KNOWN_DRAWERS))
    raw = _ask("Associated lottery person (blank for none): ")
    return raw or None


def _add_custom_prize(state: AppState) -> None:
    name = _ask("Prize name: ")
    raw_qty = _ask("Quantity: ")
    if not raw_qty.isdigit() or int(raw_qty) < 1:
        print("Quantity must be a positive integer. Prize not added.")
        return
    groups = _choose_groups(state)
    drawer = _choose_drawer()
    try:
        state.prize_manager.add_prize(name, int(raw_qty), groups, drawer)
    except ValueError as exc:
        print(f"Could not add prize: {exc}")
        return
    print(f"Prize '{name.strip()}' added.")


def _reorder_prizes(state: AppState) -> None:
    prizes = state.prize_manager.get_prizes()
    if not prizes:
        print("No prizes to reorder.")
        return
    _print_prizes(prizes)
    raw = _ask("Enter new order as serial numbers separated by spaces (e.g. 3 1 2): ")
    try:
        order = [int(t) for t in raw.replace(",", " ").split()]
    except ValueError:
        print("Order must contain only numbers. Order unchanged.")
        return
    if state.prize_manager.reorder_prizes(order):
        print("Lottery order updated.")
        _print_prizes(state.prize_manager.get_prizes())
    else:
        print("Invalid order: must contain every serial number exactly once. "
              "Order unchanged.")


def _edit_prize_groups(state: AppState) -> None:
    prizes = state.prize_manager.get_prizes()
    if not prizes:
        print("No prizes configured.")
        return
    _print_prizes(prizes)
    raw = _ask("Select prize number: ")
    if not raw.isdigit() or not (1 <= int(raw) <= len(prizes)):
        print("Invalid prize number.")
        return
    prize = prizes[int(raw) - 1]
    groups = _choose_groups(state)
    state.prize_manager.update_avoid_groups(prize.name, groups)
    print(f"Avoidance groups for '{prize.name}' updated: "
          f"{', '.join(groups) if groups else 'none'}")


# ----- lottery ---------------------------------------------------------------
def describe_rule(prize: Prize) -> str:
    drawer = prize.associated_drawer
    parts: list[str] = []
    if drawer == LI_BIN:
        parts.append("only previous winners are excluded (avoidance groups not applied)")
    else:
        parts.append("previous winners are excluded")
        if prize.avoid_groups:
            parts.append(
                "members of avoidance groups (" + ", ".join(prize.avoid_groups)
                + ") are drawn only after other members"
            )
    if drawer:
        parts.append(f"lottery person: {drawer}")
    if drawer == MA_JIAQI:
        parts.append(
            "Cheng Ru group protection applies if neither of the last two draws "
            f"by {CHEN_QIXIAN} / {JIN_DUO} produced a Cheng Ru group winner"
        )
    return "; ".join(parts)


def _await_action() -> str:
    """Wait for the user's command before drawing. Returns 'draw' or 'terminate'."""
    while True:
        cmd = _ask("Press Enter to draw, or type 'pause' / 'terminate': ").lower()
        if cmd == "":
            return "draw"
        if cmd == "terminate":
            return "terminate"
        if cmd == "pause":
            print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
            while True:
                sub = _ask("> ").lower()
                if sub == "continue":
                    print("Lottery resumed.")
                    break
                if sub == "terminate":
                    return "terminate"
                print("Please type 'continue' or 'terminate'.")
            continue
        if cmd == "continue":
            print("Lottery is not paused.")
            continue
        print("Unknown command.")


def _print_round_summary(prize: Prize, winners: list[Winner]) -> None:
    print(f"--- Round results: {prize.name} ---")
    if not winners:
        print("  (no winners drawn)")
    for i, winner in enumerate(winners, 1):
        print(f"  {i}. {winner.user.name} ({winner.user.department})")


def run_round(state: AppState, lottery: LotteryManager, prize: Prize) -> list[Winner]:
    won: list[Winner] = []
    for n in range(1, prize.quantity + 1):
        print(f"Currently drawing the {ordinal(n)} winner...")
        if _await_action() == "terminate":
            print("Current round terminated; skipping remaining draws.")
            break
        user = lottery.draw_one(prize)
        if user is None:
            print("No eligible candidates remain for this prize.")
            break
        winner = state.results.add_winner(user, prize)
        won.append(winner)
        print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")
    return won


def run_lottery(state: AppState) -> None:
    if not state.users:
        print("Please load a participant list first.")
        return
    prizes = state.prize_manager.get_prizes()
    if not prizes:
        print("Please configure prizes first.")
        return
    if state.results.get_winners():
        confirm = _ask("A lottery already has results. Restart from scratch? (y/n): ").lower()
        if confirm != "y":
            print("Lottery start cancelled.")
            return
    state.reset_lottery()
    state.lottery = LotteryManager(state.users)

    print("\n=== Lottery started ===")
    total_rounds = len(prizes)
    for round_no, prize in enumerate(prizes, 1):
        print(f"\n### Round {round_no}/{total_rounds}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {describe_rule(prize)}")
        winners = run_round(state, state.lottery, prize)
        _print_round_summary(prize, winners)

    print("\n=== All rounds completed ===")
    _print_final_summary(state, prizes)


def _print_final_summary(state: AppState, prizes: list[Prize]) -> None:
    ordered = sort_prizes_by_level(prizes)
    grouped = state.results.get_winners_by_prize(ordered)
    print("=== Winner list (by prize level, then winning order) ===")
    for prize_name, winners in grouped.items():
        print(f"[{prize_name}]")
        if not winners:
            print("  (none)")
        for i, winner in enumerate(winners, 1):
            print(f"  {i}. {winner.user.name} | {winner.user.department} | "
                  f"{prize_name} | {winner.winning_time:%Y-%m-%d %H:%M:%S}")


def menu_results(state: AppState) -> None:
    prizes = state.prize_manager.get_prizes()
    if not state.results.get_winners():
        print("No results yet.")
        return
    _print_final_summary(state, prizes)
    if _ask("Export results to file? (y/n): ").lower() == "y":
        _, message = state.results.export_to_csv(prizes)
        print(message)


# ----- main loop -------------------------------------------------------------
def _print_main_menu() -> None:
    print("\n=== Team Building Smart Lottery System ===")
    print("1. Load default team building list")
    print("2. Upload custom txt list")
    print("3. View department groups")
    print("4. Prize configuration")
    print("5. Start lottery")
    print("6. View results / export")
    print("0. Exit")


def run(state: AppState) -> None:
    while True:
        _print_main_menu()
        choice = _ask("Select: ")
        if choice == "1":
            menu_load_default(state)
        elif choice == "2":
            menu_upload_custom(state)
        elif choice == "3":
            menu_groups(state)
        elif choice == "4":
            menu_prizes(state)
        elif choice == "5":
            run_lottery(state)
        elif choice == "6":
            menu_results(state)
        elif choice == "0":
            print("Goodbye.")
            return
        else:
            print("Invalid option.")


def main() -> int:
    state = AppState()
    try:
        run(state)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
    return 0
