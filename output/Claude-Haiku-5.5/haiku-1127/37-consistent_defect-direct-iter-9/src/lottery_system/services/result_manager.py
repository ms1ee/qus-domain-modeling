"""Winner recording, grouping, prize level sorting and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = {
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
_UNRANKED = 10**6


def prize_level(name: str) -> int:
    """Return the rank of a prize from its name (1 = highest). Unranked go last."""
    for word in re.findall(r"[a-z]+", name.lower()):
        if word in _LEVEL_WORDS:
            return _LEVEL_WORDS[word]
    return _UNRANKED


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from high to low level; ties keep their given order."""
    return sorted(prizes, key=lambda p: prize_level(p.name))


@dataclass
class Winner:
    user: User
    prize_name: str
    winning_time: datetime = field(default_factory=datetime.now)
    sequence: int = 0


class ResultManager:
    """Keeps all winners in winning order."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        prize_name = prize if isinstance(prize, str) else prize.name
        winner = Winner(
            user=user,
            prize_name=prize_name,
            winning_time=datetime.now(),
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name -> winners (winning order), keyed in the given prize order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        ordered = sort_prizes_by_level(prizes)
        grouped = self.get_winners_by_prize(ordered)

        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize in ordered:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
