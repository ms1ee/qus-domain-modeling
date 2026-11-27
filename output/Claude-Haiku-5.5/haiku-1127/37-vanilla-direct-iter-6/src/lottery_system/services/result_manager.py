"""Winner recording, ordering and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

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
_UNKNOWN_LEVEL = 999


def prize_level(name: str) -> int:
    """Numeric level of a prize (1 = highest). Unknown levels sort last."""
    lowered = name.casefold()
    for word, level in _LEVEL_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            return level
    match = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", lowered)
    if match:
        return int(match.group(1))
    return _UNKNOWN_LEVEL


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from high level to low; ties keep configured order."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level(item[1].name), item[0]))
    return [prize for _, prize in indexed]


@dataclass(frozen=True)
class Winner:
    user: User
    prize_name: str
    prize_order: int      # winning order within the same prize (1-based)
    winning_time: str


class ResultManager:
    """Keeps the complete winner list for the lottery session."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        same_prize = sum(1 for w in self._winners if w.prize_name == prize.name)
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_order=same_prize + 1,
            winning_time=datetime.now().strftime(TIME_FORMAT),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            if prize.name in result:
                continue
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        by_prize = self.get_winners_by_prize(prizes)
        filename = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(filename, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in by_prize.items():
                    for winner in winners:
                        writer.writerow(
                            [winner.user.name, winner.user.department, prize_name, winner.winning_time]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {filename}"
