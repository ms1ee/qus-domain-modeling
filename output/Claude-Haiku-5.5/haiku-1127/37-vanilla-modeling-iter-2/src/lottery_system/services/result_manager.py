"""Winner records, ordering, display grouping and CSV/TXT export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3}


def prize_level(name: str) -> int:
    """Map 'First'/'Second'/'Third' in a prize name to level 1/2/3.
    Prizes without a level word are ranked after leveled prizes."""
    match = re.search(r"\b(first|second|third)\b", name, re.IGNORECASE)
    if match:
        return _LEVEL_WORDS[match.group(1).lower()]
    return 99


@dataclass
class Winner:
    user: User
    prize: Prize
    winning_time: datetime
    sequence: int


def _ordered_prizes(prizes: list[Prize]) -> list[Prize]:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda pair: (prize_level(pair[1].name), pair[0]))
    return [prize for _, prize in indexed]


class ResultManager:
    """Keeps all winners in real time and produces ordered views/exports."""

    HEADER = ["Name", "Department", "Prize Name", "Winning Time"]

    def __init__(self):
        self._winners: list[Winner] = []
        self._counter = 0

    @property
    def winners(self) -> list[Winner]:
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._counter += 1
        winner = Winner(user, prize, datetime.now(), self._counter)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Keys are prize names ordered by level (high to low, i.e. First first);
        values are winners of that prize in winning-time order."""
        result: dict[str, list[Winner]] = {}
        for prize in _ordered_prizes(prizes):
            bucket = result.setdefault(prize.name, [])
            bucket.extend(w for w in self._winners if w.prize is prize)
        return result

    def _ordered_winners(self, prizes: list[Prize]) -> list[Winner]:
        ordered: list[Winner] = []
        for bucket in self.get_winners_by_prize(prizes).values():
            ordered.extend(bucket)
        return ordered

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        winners = self._ordered_winners(prizes)
        if not winners:
            return False, "No winners to export."
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(self.HEADER)
                for winner in winners:
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize.name,
                        f"{winner.winning_time:%Y-%m-%d %H:%M:%S}",
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
