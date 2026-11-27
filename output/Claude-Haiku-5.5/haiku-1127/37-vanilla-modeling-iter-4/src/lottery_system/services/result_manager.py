"""Winner recording, grouping, sorting and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.constants import RESULT_FILE_PREFIX
from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores all winners in winning order and produces summaries/exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            result.setdefault(winner.prize_name, []).append(winner)
        return result

    def sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners ordered by prize level (high to low), then prize sequence, then winning order."""
        index_map = {prize.name: index for index, prize in enumerate(prizes)}
        fallback_index = len(prizes)
        return sorted(
            self._winners,
            key=lambda w: (w.prize_level, index_map.get(w.prize_name, fallback_index), w.winning_order),
        )

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        if not self._winners:
            return False, "No winners to export."

        file_name = f"{RESULT_FILE_PREFIX}{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self.sorted_winners(prizes):
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
