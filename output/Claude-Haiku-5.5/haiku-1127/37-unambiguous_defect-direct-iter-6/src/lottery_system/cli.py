"""Command-line interface: list setup, prize setup, lottery control and results."""

from __future__ import annotations

import queue
import sys
import threading
import time

from .models import Prize, User
from .services.list_manager import ListManager
from .services.lottery_manager import LotteryManager
from .services.prize_manager import PrizeManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class CommandReader:
    """Reads stdin in a background thread so commands can be polled during the lottery.

    A None item in the queue marks end of input.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            for line in sys.stdin:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(None)

    def _take(self, line):
        if line is None:
            raise EOFError("Input closed")
        return line

    def ask(self, prompt: str = "") -> str:
        print(prompt, end="", flush=True)
        return self._take(self._queue.get())

    def wait(self) -> str:
        return self._take(self._queue.get())

    def poll(self) -> str | None:
        """Return the next queued line, or None if nothing is waiting."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        return self._take(item)


class LotterySystemApp:
    def __init__(self, reader: CommandReader, draw_delay: float = 0.8) -> None:
        self.reader = reader
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery_manager: LotteryManager | None = None

    # ----- input helpers -----
    def _ask(self, prompt: str) -> str:
        return self.reader.ask(prompt)

    def _ask_yes_no(self, prompt: str) -> bool:
        while True:
            answer = self._ask(prompt).strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print("Please answer 'y' or 'n'.")

    def _ask_choice(self, prompt: str, options: tuple[str, ...]) -> str:
        while True:
            answer = self._ask(prompt).strip().lower()
            if answer in options:
                return answer
            print("Invalid choice, please try again.")

    # ----- step 1: participant list -----
    def _setup_users(self) -> bool:
        while True:
            print("\n=== Step 1: Participant List ===")
            print("1. Load built-in default team building list")
            print("2. Upload custom txt list (Name,Department per line)")
            print("q. Quit")
            choice = self._ask("Select: ").strip().lower()

            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self._ask("Path to txt file: ").strip().strip('"').strip("'")
                users, errors = self.list_manager.load_custom_list(path)
            elif choice == "q":
                return False
            else:
                print("Invalid option.")
                continue

            verified = self._verify_list(users, errors)
            if verified is None:
                print("Upload terminated.")
                continue
            if not verified:
                print("No valid participants loaded.")
                continue

            self.users = verified
            print(f"Loaded {len(self.users)} participant(s).")
            self._show_groups()
            return True

    def _verify_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Returns the verified user list, or None if the upload was terminated."""
        if errors:
            print(f"Found {len(errors)} format error(s):")
            for error in errors:
                print("  " + error)
            choice = self._ask_choice(
                "[r] remove invalid data and continue / [t] terminate upload: ", ("r", "t")
            )
            if choice == "t":
                return None

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            choice = self._ask_choice(
                "[r] remove duplicates (keep first occurrence) and continue / [t] terminate upload: ",
                ("r", "t"),
            )
            if choice == "t":
                return None
            return valid
        return valid

    def _show_groups(self) -> None:
        groups = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in groups.items():
            print(f"  {group}: {count} people")
        print(f"  Total: {sum(groups.values())} people")

    # ----- step 2: prizes -----
    def _setup_prizes(self) -> None:
        print("\n=== Step 2: Prize Configuration ===")
        if self._ask_yes_no("Load preset prizes? (y/n): "):
            for error in self.prize_manager.load_default_prizes():
                print("  " + error)

        while not self.prize_manager.get_prizes() or self._ask_yes_no(
            "Add a custom prize? (y/n): "
        ):
            self._add_custom_prize()

        self._show_prizes()
        self._configure_order()

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            print("Prize name cannot be empty.")
            return

        while True:
            raw = self._ask("Quantity: ").strip()
            if raw.isdigit() and int(raw) > 0:
                quantity = int(raw)
                break
            print("Quantity must be a positive integer.")

        groups = self._select_avoid_groups()
        drawer = self._ask("Associated lottery person (Enter to skip): ").strip() or None

        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _select_avoid_groups(self) -> list[str]:
        groups = sorted(self.list_manager.get_group_info(self.users).keys())
        print("Available department groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        raw = self._ask("Avoid groups (numbers or names, comma-separated; Enter for none): ").strip()
        if not raw:
            return []

        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                group = groups[int(token) - 1]
            else:
                group = next((g for g in groups if g.casefold() == token.casefold()), None)
                if group is None:
                    print(f"Unknown group '{token}', ignored.")
                    continue
            if group not in selected:
                selected.append(group)
        return selected

    def _show_prizes(self) -> None:
        print("Current round order:")
        for index, prize in enumerate(self.prize_manager.get_prizes(), start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {index}. {prize.name} | qty {prize.quantity} | avoid: {avoid} | drawer: {drawer}")

    def _configure_order(self) -> None:
        while True:
            raw = self._ask(
                "Enter new round order as serial numbers (e.g. 2 1 3), or Enter to keep: "
            ).strip()
            if not raw:
                return
            try:
                order = [int(token) for token in raw.replace(",", " ").split()]
            except ValueError:
                print("Please enter integers only.")
                continue
            if self.prize_manager.reorder_prizes(order):
                print("Round order updated.")
                self._show_prizes()
                return
            print("Invalid order: each serial number must appear exactly once.")

    # ----- step 3: lottery -----
    def _handle_commands(self) -> str | None:
        """Process queued operator commands. Returns 'terminate' to skip the round."""
        while True:
            line = self.reader.poll()
            if line is None:
                return None
            command = line.strip().lower()
            if not command:
                continue
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
                while True:
                    reply = self.reader.wait().strip().lower()
                    if reply == "continue":
                        print("Lottery resumed.")
                        break
                    if reply == "terminate":
                        return "terminate"
                    print("While paused, type 'continue' or 'terminate'.")
                continue
            if command == "terminate":
                return "terminate"
            if command == "continue":
                print("Lottery is not paused.")
                continue
            print(f"Unknown command '{line.strip()}'. Available: pause, continue, terminate.")

    def _run_round(self, index: int, prize: Prize, total: int) -> None:
        manager = self.lottery_manager
        assert manager is not None
        print(f"\n=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {manager.describe_rules(prize)}")

        won: list[User] = []
        for pick in range(1, prize.quantity + 1):
            if self._handle_commands() == "terminate":
                print("Round terminated by operator; skipping remaining picks.")
                break

            print(f"Currently drawing the {ordinal(pick)} winner...")
            time.sleep(self.draw_delay)

            if self._handle_commands() == "terminate":
                print("Round terminated by operator; skipping remaining picks.")
                break

            if manager.is_fallback_active(prize):
                print("  [Cheng Ru Group protection active: pool limited to Cheng Ru Group members]")
            user = manager.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            won.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        print(f"--- Round {index} results ({len(won)}/{prize.quantity}) ---")
        for number, user in enumerate(won, start=1):
            print(f"  {number}. {user.name} ({user.department})")

    def _run_lottery(self) -> None:
        if not self._ask_yes_no("Start the lottery now? (y/n): "):
            return

        self.lottery_manager = LotteryManager(self.users)
        prizes = self.prize_manager.get_prizes()
        print("\nLottery started. Commands: pause / continue / terminate")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, prize, len(prizes))
        print("\nAll rounds completed.")

    def _show_final_results(self) -> None:
        assert self.lottery_manager is not None
        prizes = self.prize_manager.get_prizes()
        grouped = self.lottery_manager.result_manager.get_winners_by_prize(prizes)
        print("\n=== Final Results ===")
        for prize_name, winners in grouped.items():
            print(prize_name)
            if not winners:
                print("  (no winners)")
            for number, winner in enumerate(winners, start=1):
                print(f"  {number}. {winner.user.name} ({winner.user.department})")

        if self._ask_yes_no("Export winner list to file? (y/n): "):
            _, message = self.lottery_manager.result_manager.export_to_csv(prizes)[0:1] + (
                self.lottery_manager.result_manager.export_to_csv(prizes)[1],
            )
            print(message)

    # ----- main flow -----
    def run(self) -> int:
        print("=== Company Team Building Smart Lottery System ===")
        if not self._setup_users():
            print("Goodbye.")
            return 0
        self._setup_prizes()
        self._run_lottery()
        if self.lottery_manager is not None:
            self._show_final_results()
        print("Goodbye.")
        return 0


def main() -> int:
    try:
        app = LotterySystemApp(CommandReader())
        return app.run()
    except EOFError:
        print("\nInput closed, exiting.")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")
        return 130
