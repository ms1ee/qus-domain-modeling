"""Winner recording, grouped result views and CSV-format export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = {
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
}
_LEVEL_PATTERN = re.compile(
    r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\b", re.IGNORECASE
)
_UNRANKED = 999


def prize_level_rank(name: str) -> int:
    """Return the level rank of a prize (1 = highest). Unranked prizes go last."""
    match = _LEVEL_PATTERN.search(name)
    if not match:
        return _UNRANKED
    return _LEVEL_WORDS[match.group(1).lower()]


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int
    won_at: str


class ResultManager:
    """Stores winners and produces result views and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            sequence=len(self._winners) + 1,
            won_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level then winning time."""
        indexed = sorted(
            enumerate(prizes),
            key=lambda item: (prize_level_rank(item[1].name), item[0]),
        )
        result: dict[str, list[Winner]] = {}
        for _, prize in indexed:
            matched = [w for w in self._winners if w.prize_name == prize.name]
            result[prize.name] = sorted(matched, key=lambda w: w.sequence)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to the current directory."""
        grouped = self.get_winners_by_prize(prizes)
        rows: list[Winner] = [w for items in grouped.values() for w in items]
        known = set(grouped.keys())
        rows.extend(w for w in self._winners if w.prize_name not in known)

        date_text = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.won_at,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
