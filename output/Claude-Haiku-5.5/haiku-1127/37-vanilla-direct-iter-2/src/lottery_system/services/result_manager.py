"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User

_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
_LEVEL_RE = re.compile(
    r"^\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+prize\b",
    re.IGNORECASE,
)


def prize_level(name: str) -> int:
    """Smaller number means higher prize level. Unranked prizes come last."""
    match = _LEVEL_RE.match(name or "")
    if match:
        return _ORDINALS[match.group(1).lower()]
    return len(_ORDINALS) + 1


def sorted_prizes(prizes) -> list[Prize]:
    """Sort prizes by level from high to low, keeping addition order within a level."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level(item[1].name), item[0]))
    return [prize for _, prize in indexed]


@dataclass(frozen=True)
class Winner:
    """A winning record.

    order: winning time sequence number (1-based, across all rounds).
    """

    user: User
    prize_name: str
    order: int


class ResultManager:
    """Keeps all winners in winning order."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize_name=prize.name, order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Winners grouped by prize name, prizes ordered from high to low level."""
        grouped: dict[str, list[Winner]] = {}
        for prize in sorted_prizes(prizes):
            grouped[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return grouped

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for winners in grouped.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        filename = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.order,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
