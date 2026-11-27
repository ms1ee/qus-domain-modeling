"""Winner recording, grouping and CSV-style export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores all winning records of the event."""

    def __init__(self):
        self._winners: list[Winner] = []
        self._order_counter: int = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._order_counter += 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=self._order_counter,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low).

        Within each prize, winners are ordered by winning time/order.
        """
        result: dict[str, list[Winner]] = {}
        for prize in sorted(prizes, key=lambda p: p.level):
            winners = [w for w in self._winners if w.prize_name == prize.name]
            winners.sort(key=lambda w: w.winning_order)
            result[prize.name] = winners
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [w for winners in grouped.values() for w in winners]
        if not rows:
            return False, "No winners to export."

        now = datetime.now()
        file_path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for w in rows:
                    writer.writerow([
                        w.user.name,
                        w.user.department,
                        w.prize_name,
                        w.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {file_path}"
