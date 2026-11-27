"""Winner recording, grouping, and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, prize_level

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    won_at: datetime
    sequence: int


class ResultManager:
    """Maintains the winner list in real time."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            won_at=datetime.now(),
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    @staticmethod
    def _sorted_prizes(prizes: list[Prize]) -> list[Prize]:
        return sorted(prizes, key=lambda prize: prize_level(prize.name))

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low)."""
        result: dict[str, list[Winner]] = {}
        for prize in self._sorted_prizes(prizes):
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def _ordered_winners(self, prizes: list[Prize]) -> list[Winner]:
        ordered: list[Winner] = []
        for prize in self._sorted_prizes(prizes):
            ordered.extend(w for w in self._winners if w.prize_name == prize.name)
        return ordered

    def export_to_csv(self, prizes: list[Prize], directory: str | None = None) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        winners = self._ordered_winners(prizes)
        if not winners:
            return False, "No winners to export."

        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(directory or os.getcwd(), file_name)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in winners:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.won_at.strftime(TIME_FORMAT),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
