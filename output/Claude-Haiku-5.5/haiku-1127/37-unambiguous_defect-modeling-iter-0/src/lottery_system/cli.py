"""Command-line interface for the team building lottery system."""

import re
import time

from lottery_system.console import InputReader
from lottery_system.constants import CHENG_RU_GROUP, CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import normalize_text
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MENU_ITEMS = (
    ("1", "Load built-in default team building list"),
    ("2", "Upload custom txt participant list"),
    ("3", "View department groups and member counts"),
    ("4", "Load preset prize library"),
    ("5", "Add custom prize"),
    ("6", "View prize list (lottery sequence)"),
    ("7", "Reorder prizes (lottery sequence)"),
    ("8", "Start lottery"),
    ("9", "View winner list"),
    ("10", "Export winner list to txt (CSV format)"),
    ("0", "Exit"),
)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class _RoundState:
    def __init__(self):
        self.paused = False
        self.terminated = False


class LotteryApp:
    def __init__(self, reader=None, draw_delay: float = 1.0):
        self.reader = reader if reader is not None else InputReader()
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.last_result: ResultManager | None = None
        self.last_prizes = []

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        value = self.reader.read_line(prompt)
        return "" if value is None else value

    def _print_menu(self) -> None:
        print("\n========== Team Building Smart Lottery ==========")
        for key, label in MENU_ITEMS:
            print(f"  {key:>2}. {label}")
        print("=================================================")

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            self._print_menu()
            choice = self.reader.read_line("Select an option: ")
            if choice is None:
                print("\nInput closed. Exiting.")
                break
            choice = choice.strip()
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._upload_custom_list()
            elif choice == "3":
                self._view_groups()
            elif choice == "4":
                self._load_default_prizes()
            elif choice == "5":
                self._add_prize()
            elif choice == "6":
                self._view_prizes()
            elif choice == "7":
                self._reorder_prizes()
            elif choice == "8":
                self._start_lottery()
            elif choice == "9":
                self._view_results()
            elif choice == "10":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option, please try again.")
            if self.reader.closed:
                print("\nInput closed. Exiting.")
                break

    # ------------------------------------------------------------ list module
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._finalize_list(users, errors, "built-in default list")

    def _upload_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt participant list: ").strip().strip('"')
        if not path:
            print("No path entered. Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._finalize_list(users, errors, path)

    def _finalize_list(self, users, errors, source: str) -> None:
        if errors:
            print(f"Validation issues found in {source}:")
            for error in errors:
                print(f"  - {error}")
        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print("Duplicate names detected (later occurrences will be removed):")
            for dup in duplicates:
                print(f"  - {dup.name} ({dup.department})")

        if not errors and not duplicates:
            self.users = valid
            print(f"Loaded {len(valid)} participants from {source}.")
            self._view_groups()
            return

        if not users:
            print("No participant data could be read. Upload terminated; list unchanged.")
            return

        print("\nChoose how to proceed:")
        print("  1. Remove invalid and duplicate data and continue")
        print("  2. Terminate upload")
        choice = self._ask("Select 1 or 2: ").strip()
        if choice == "1":
            if not valid:
                print("No valid participants remain. Upload terminated; list unchanged.")
                return
            self.users = valid
            removed = len(errors) + len(duplicates)
            print(f"Loaded {len(valid)} participants (removed {removed} invalid/duplicate entries).")
            self._view_groups()
        else:
            print("Upload terminated; participant list unchanged.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded. Please load a list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid department groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} people")
        print(f"Total: {len(self.users)} participants in {len(info)} groups")

    # ------------------------------------------------------------ prize module
    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            print(f"  - {error}")
        print("Preset prize library loaded.")
        self._view_prizes()

    def _select_avoid_groups(self) -> list[str] | None:
        groups = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        if groups:
            print("Available groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        while True:
            text = self._ask("Avoidance groups (numbers or names, comma separated; empty for none): ")
            if not text.strip():
                return []
            tokens = [t.strip() for t in re.split(r"[,，]", text) if t.strip()]
            selected: list[str] = []
            valid = True
            for token in tokens:
                if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                    match = groups[int(token) - 1]
                else:
                    match = next(
                        (g for g in groups if normalize_text(g) == normalize_text(token)), None
                    )
                    if match is None:
                        if not groups:
                            match = token
                        else:
                            print(f"Invalid group: '{token}'. Please try again.")
                            valid = False
                            break
                if match not in selected:
                    selected.append(match)
            if valid:
                return selected

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Prize quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be a positive integer.")
            return
        avoid = self._select_avoid_groups()
        drawer = self._ask("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, quantity, avoid, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {name}")

    def _print_prizes(self, prizes) -> None:
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            avoid = ", ".join(prize.avoid_groups) or "-"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {avoid}"
            )

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        print("Prize lottery sequence:")
        self._print_prizes(prizes)

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        print("Current sequence:")
        self._print_prizes(prizes)
        text = self._ask(
            f"Enter the new order as serial numbers 1-{len(prizes)} (e.g. '3 1 2'), empty to keep: "
        ).strip()
        if not text:
            print("Sequence unchanged.")
            return
        try:
            order = [int(t) for t in re.split(r"[\s,]+", text) if t]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if not self.prize_manager.reorder_prizes(order):
            print("Invalid order: each serial number must appear exactly once.")
            return
        print("New sequence:")
        self._print_prizes(self.prize_manager.get_prizes())

    # ------------------------------------------------------- lottery process
    @staticmethod
    def _describe_rules(prize, manager: LotteryManager) -> str:
        rules = ["exclude previous winners"]
        drawer = normalize_text(prize.associated_drawer or "")
        if drawer == normalize_text(LI_BIN):
            rules.append("relaxed rules for Li Bin (avoidance groups not applied)")
        elif prize.avoid_groups:
            rules.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if drawer == normalize_text(MA_JIAQI):
            if manager.is_fallback_active_for(prize):
                rules.append(
                    f"Cheng Ru group protection active: pool limited to {CHENG_RU_GROUP} members"
                )
            else:
                rules.append(
                    f"Cheng Ru group protection applies if the last two draws by "
                    f"{CHEN_QIXIAN} and {JIN_DUO} had no {CHENG_RU_GROUP} winner"
                )
        return "; ".join(rules)

    def _handle_command(self, command, state: _RoundState) -> None:
        if command is None:
            return
        cmd = command.strip().lower()
        if not cmd:
            return
        if cmd == "pause":
            if state.terminated:
                return
            state.paused = True
            print("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
        elif cmd == "continue":
            if state.paused:
                state.paused = False
                print("Lottery resumed.")
            else:
                print("Lottery is not paused.")
        elif cmd == "terminate":
            state.terminated = True
            state.paused = False
            print("Terminating current round...")
        else:
            print("Unknown command. Available commands: pause, continue, terminate")

    def _drain_commands(self, state: _RoundState) -> None:
        while True:
            command = self.reader.poll()
            if command is None:
                break
            self._handle_command(command, state)

    def _wait_while_paused(self, state: _RoundState) -> None:
        while True:
            self._drain_commands(state)
            if state.terminated or not state.paused:
                return
            command = self.reader.read_line("(paused) > ")
            if command is None:
                # Input closed while paused: resume so the lottery can complete.
                state.paused = False
                return
            self._handle_command(command, state)

    def _interval(self, state: _RoundState) -> None:
        end = time.monotonic() + self.draw_delay
        while True:
            self._drain_commands(state)
            if state.terminated or state.paused:
                return
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

    def _run_round(self, round_no: int, prize, manager: LotteryManager) -> list:
        print(f"\n=== Round {round_no}: {prize.name} ===")
        print(f"Quantity: {prize.quantity} | Lottery person: {prize.associated_drawer or '-'}")
        print(f"Rule: {self._describe_rules(prize, manager)}")

        state = _RoundState()
        round_winners = []
        for order in range(1, prize.quantity + 1):
            self._wait_while_paused(state)
            if state.terminated:
                print("Current round terminated; skipping remaining winners.")
                break
            print(f"Currently drawing the {ordinal(order)} winner...")
            user = manager.draw_next(prize)
            if user is None:
                print("No eligible participants remain for this prize.")
                break
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            if order < prize.quantity:
                self._interval(state)

        manager.end_round(prize, round_winners)
        print(f"Round {round_no} finished: {len(round_winners)}/{prize.quantity} winners drawn.")
        if round_winners:
            print("Round results in winning order:")
            for index, user in enumerate(round_winners, start=1):
                print(f"  {index}. {user.name} ({user.department})")
        return round_winners

    def _start_lottery(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please load or add prizes first.")
            return
        if not self.users:
            print("No participants loaded. Please load a participant list first.")
            return

        print("\nLottery starts! Commands: pause / continue / terminate")
        result = ResultManager()
        manager = LotteryManager(self.users)
        for round_no, prize in enumerate(prizes, start=1):
            if manager.is_fallback_active_for(prize):
                print(f"Notice: Cheng Ru group protection is active for {prize.name}.")
            winners = self._run_round(round_no, prize, manager)
            for user in winners:
                result.add_winner(user, prize)

        self.last_result = result
        self.last_prizes = prizes
        print("\nAll rounds completed.")
        self._print_result_summary(result, prizes)

    # ------------------------------------------------------------ results
    def _print_result_summary(self, result: ResultManager, prizes) -> None:
        print("\n=== Winner List (by prize level, then winning order) ===")
        grouped = result.get_winners_by_prize(prizes)
        for prize_name, winners in grouped.items():
            print(f"\n[{prize_name}]")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.user.name} ({winner.user.department}) "
                    f"- {winner.prize_name}"
                )

    def _view_results(self) -> None:
        if self.last_result is None:
            print("No lottery results yet.")
            return
        self._print_result_summary(self.last_result, self.last_prizes)

    def _export_results(self) -> None:
        if self.last_result is None:
            print("No lottery results to export. Please run the lottery first.")
            return
        success, message = self.last_result.export_to_csv(self.last_prizes)
        print(message)


def main() -> None:
    app = LotteryApp()
    app.run()
