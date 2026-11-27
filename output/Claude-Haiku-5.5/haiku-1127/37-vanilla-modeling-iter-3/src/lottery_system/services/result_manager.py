"""Winner recording, ordering, and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, prize_level


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores winners and produces ordered results and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the given prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in the order they were drawn."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, each list in winning time order."""
        return {
            prize.name: [w for w in self._winners if w.prize_name == prize.name]
            for prize in prizes
        }

    def get_sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Return winners sorted by prize level (high to low), then prize sequence,
        then winning time order."""
        prize_index = {prize.name: idx for idx, prize in enumerate(prizes)}
        fallback_index = len(prize_index)

        def sort_key(winner: Winner) -> tuple[int, int, int]:
            return (
                prize_level(winner.prize_name),
                prize_index.get(winner.prize_name, fallback_index),
                winner.winning_order,
            )

        return sorted(self._winners, key=sort_key)

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in CSV format."""
        file_name = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self.get_sorted_winners(prizes):
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
