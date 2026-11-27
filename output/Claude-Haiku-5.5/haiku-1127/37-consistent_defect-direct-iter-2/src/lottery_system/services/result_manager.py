"""Winner recording, grouping by prize level, and CSV export."""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


_LEVEL_WORDS = ("first", "second", "third")
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int = 0
    won_at: datetime = field(default_factory=datetime.now)


def _prize_rank(name: str) -> int:
    """Return the level rank of a prize (1 = highest). Unknown levels rank last."""
    lowered = name.casefold()
    for index, word in enumerate(_LEVEL_WORDS, start=1):
        if re.search(rf"\b{word}\b", lowered):
            return index
    return len(_LEVEL_WORDS) + 1


class ResultManager:
    """Stores winners and produces ordered summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the given prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            sequence=len(self._winners) + 1,
            won_at=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered from highest prize level to lowest.

        Within the same prize, winners are in winning time order.
        """
        ordered = sorted(
            enumerate(prizes),
            key=lambda item: (_prize_rank(item[1].name), item[0]),
        )
        result: dict[str, list[Winner]] = {prize.name: [] for _, prize in ordered}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt."""
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winners in grouped.values():
                    for winner in winners:
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.won_at.strftime(_TIME_FORMAT),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
