"""Winner recording, ordering, display grouping and CSV-style export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = (("first", 1), ("second", 2), ("third", 3), ("fourth", 4), ("fifth", 5))
_UNRANKED = 999


def prize_rank(name: str) -> int:
    """Return the prize level (1 = highest). Unknown levels are ranked last."""
    lowered = name.casefold()
    for word, rank in _LEVEL_WORDS:
        if re.search(rf"\b{word}\b", lowered):
            return rank
    return _UNRANKED


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int          # global winning order (1-based)
    won_at: datetime       # real winning timestamp


class ResultManager:
    """Stores winners and produces ordered results."""

    EXPORT_HEADER = ["Name", "Department", "Prize Name", "Winning Time"]

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._counter = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the prize."""
        self._counter += 1
        winner = Winner(user, prize.name, self._counter, datetime.now())
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    @staticmethod
    def _ordered_prizes(prizes: list[Prize]) -> list[Prize]:
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (prize_rank(item[1].name), item[0]))
        return [prize for _, prize in indexed]

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name -> winners, ordered by prize level (high to low).

        Winners within a prize are ordered by winning time.
        """
        result: dict[str, list[Winner]] = {}
        for prize in self._ordered_prizes(prizes):
            winners = [w for w in self._winners if w.prize_name == prize.name]
            result[prize.name] = sorted(winners, key=lambda w: w.sequence)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in the current directory."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for winners in grouped.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(self.EXPORT_HEADER)
                for winner in rows:
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize_name,
                        winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
