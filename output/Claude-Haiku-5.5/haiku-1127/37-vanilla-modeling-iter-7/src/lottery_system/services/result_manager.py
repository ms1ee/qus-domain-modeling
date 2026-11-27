"""Winner recording, grouping and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.config import EXPORT_FILE_PREFIX
from lottery_system.models import Prize, User

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores all winners in winning order."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize. Returns the created record."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map each prize name to its winners, ordered by winning order."""
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt.

        Rows are ordered by prize level (high to low), then winning order.
        """
        now = datetime.now()
        file_path = os.path.join(os.getcwd(), f"{EXPORT_FILE_PREFIX}{now:%Y%m%d}.txt")
        grouped = self.get_winners_by_prize(prizes)
        ordered_prizes = sorted(prizes, key=lambda prize: prize.level)
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize in ordered_prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow(
                            [
                                winner.user.name,
                                winner.user.department,
                                winner.prize_name,
                                winner.winning_time.strftime(TIME_FORMAT),
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {file_path}"
