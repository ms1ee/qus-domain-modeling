"""Winner recording, ordering, display grouping and CSV/txt export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_time: datetime
    winning_order: int


def sort_prizes(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes by level from high (First) to low; unknown levels keep addition order after leveled ones."""
    indexed = list(enumerate(prizes))
    indexed.sort(
        key=lambda item: (
            item[1].level if item[1].level is not None else 1000 + item[0],
            item[0],
        )
    )
    return [prize for _, prize in indexed]


class ResultManager:
    """Keeps the winner list and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._winner_names: set[str] = set()

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. Raises ValueError if the person already won."""
        if user.name in self._winner_names:
            raise ValueError(f"{user.name} has already won a prize")
        winner = Winner(
            user=user,
            prize=prize,
            winning_time=datetime.now(),
            winning_order=len(self._winners) + 1,
        )
        self._winners.append(winner)
        self._winner_names.add(user.name)
        return winner

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Winners grouped by prize name, prizes ordered high level to low, winners in winning order."""
        ordered = sort_prizes(prizes)
        result: dict[str, list[Winner]] = {prize.name: [] for prize in ordered}
        for winner in self._winners:
            if winner.prize.name in result:
                result[winner.prize.name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to 'awards_result_YYYYMMDD.txt' in the current directory as CSV."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for winners in grouped.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize.name,
                        winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
