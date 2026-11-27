"""Command-line interface for the team building lottery system."""

from __future__ import annotations

import re
from typing import Callable

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_process import LotteryProcess, describe_rules
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, ordered_prizes


class LotteryCLI:
    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self._ask = input_func
        self._say = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.results: ResultManager | None = None
        self.result_prizes: list[Prize] = []

    # ---------- main loop ----------
    def run(self) -> None:
        self._say("=== Company Team Building Smart Lottery System ===")
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._upload_custom_list()
            elif choice == "3":
                self._view_groups()
            elif choice == "4":
                self._prize_menu()
            elif choice == "5":
                self._start_lottery()
            elif choice == "6":
                self._view_results()
            elif choice == "7":
                self._export_results()
            elif choice == "0":
                self._say("Goodbye.")
                return
            else:
                self._say("Invalid option, please try again.")

    def _print_main_menu(self) -> None:
        self._say("")
        self._say("---------------- Main Menu ----------------")
        self._say("1. Load built-in team building list")
        self._say("2. Upload custom txt list")
        self._say("3. View department groups")
        self._say("4. Prize configuration")
        self._say("5. Start lottery")
        self._say("6. View winner results")
        self._say("7. Export results to file")
        self._say("0. Exit")

    # ---------- list management ----------
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._finalize_users(users, errors)

    def _upload_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file (format: Name,Department Group): ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        self._finalize_users(users, errors)

    def _finalize_users(self, users: list[User], errors: list[str]) -> None:
        if not users:
            self._say("Upload failed: no valid data loaded.")
            for error in errors:
                self._say(f"  {error}")
            return
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            self._say("Verification found problems:")
            for error in errors:
                self._say(f"  {error}")
            for duplicate in duplicates:
                self._say(f"  Duplicate Name: {duplicate.name} ({duplicate.department})")
            choice = self._ask(
                "Enter 'r' to remove invalid/duplicate data and keep valid entries, "
                "or 'q' to terminate the upload: "
            ).strip().lower()
            if choice != "r":
                self._say("Upload terminated. Previous list unchanged.")
                return
        self.users = valid
        self._say(f"Loaded {len(self.users)} participants.")
        self._view_groups()

    def _view_groups(self) -> None:
        if not self.users:
            self._say("No participant list loaded.")
            return
        groups = self.list_manager.get_group_info(self.users)
        self._say("Department groups:")
        for index, (group, count) in enumerate(groups.items(), start=1):
            self._say(f"  {index}. {group}: {count} people")

    # ---------- prize configuration ----------
    def _prize_menu(self) -> None:
        while True:
            self._say("")
            self._say("------------ Prize Configuration ------------")
            self._say("1. Load preset prizes")
            self._say("2. Add custom prize")
            self._say("3. View prizes")
            self._say("4. Set avoidance groups for a prize")
            self._say("5. Reorder lottery sequence")
            self._say("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._say(f"  {error}")
                self._say("Preset prizes loaded.")
            elif choice == "2":
                self._add_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._set_prize_avoid_groups()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                self._say("Invalid option, please try again.")

    def _view_prizes(self) -> list[Prize]:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return prizes
        self._say("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._say(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoidance groups: {groups}"
            )
        return prizes

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be a positive integer.")
            return
        groups = self._select_groups("Avoidance groups (numbers or names, comma separated; blank for none): ")
        drawer = self._ask("Associated lottery person (blank for none): ").strip()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer or None)
        except ValueError as exc:
            self._say(f"Failed to add prize: {exc}")
            return
        self._say(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _set_prize_avoid_groups(self) -> None:
        prizes = self._view_prizes()
        if not prizes:
            return
        text = self._ask("Select prize number: ").strip()
        if not text.isdigit() or not (1 <= int(text) <= len(prizes)):
            self._say("Invalid prize number.")
            return
        prize = prizes[int(text) - 1]
        groups = self._select_groups("Avoidance groups (numbers or names, comma separated; blank for none): ")
        if self.prize_manager.set_avoid_groups(prize.name, groups):
            self._say(f"Avoidance groups updated for {prize.name}.")
        else:
            self._say("Failed to update avoidance groups.")

    def _reorder_prizes(self) -> None:
        prizes = self._view_prizes()
        if not prizes:
            return
        text = self._ask(
            "Enter the new sequence as current serial numbers separated by spaces (e.g. 2 1 3): "
        )
        tokens = text.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            self._say("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Lottery sequence updated.")
            self._view_prizes()
        else:
            self._say("Invalid order: each serial number must appear exactly once.")

    def _select_groups(self, prompt: str) -> list[str]:
        group_names = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        if group_names:
            self._say("Available groups:")
            for index, group in enumerate(group_names, start=1):
                self._say(f"  {index}. {group}")
        text = self._ask(prompt).strip()
        selected: list[str] = []
        for token in re.split(r"[,，]", text):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(group_names):
                name = group_names[int(token) - 1]
            elif token in group_names:
                name = token
            else:
                self._say(f"  Ignored unknown group: {token}")
                continue
            if name not in selected:
                selected.append(name)
        return selected

    # ---------- lottery ----------
    def _start_lottery(self) -> None:
        if not self.users:
            self._say("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("Please configure prizes first.")
            return
        confirm = self._ask("Start the lottery now? (y/n): ").strip().lower()
        if confirm != "y":
            self._say("Lottery cancelled.")
            return
        process = LotteryProcess(self.users, prizes, input_func=self._ask, output_func=self._say)
        results = process.run()
        self.results = results
        self.result_prizes = prizes
        self._say("")
        self._say("Lottery finished. Final winner list:")
        self._print_summary()

    # ---------- results ----------
    def _view_results(self) -> None:
        if self.results is None:
            self._say("No lottery results yet.")
            return
        self._print_summary()

    def _print_summary(self) -> None:
        if self.results is None:
            return
        by_prize = self.results.get_winners_by_prize(self.result_prizes)
        for prize in ordered_prizes(self.result_prizes):
            self._say(f"{prize.name}:")
            winners = by_prize.get(prize.name, [])
            if not winners:
                self._say("  (no winners)")
            for position, winner in enumerate(winners, start=1):
                self._say(f"  {position}. {winner.user.name} ({winner.user.department})")

    def _export_results(self) -> None:
        if self.results is None:
            self._say("No lottery results to export.")
            return
        _, message = self.results.export_to_csv(self.result_prizes)
        self._say(message)


def main() -> None:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
