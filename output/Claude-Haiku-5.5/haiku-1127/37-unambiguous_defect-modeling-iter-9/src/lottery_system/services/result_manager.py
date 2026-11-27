"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import datetime
import os
import re
from dataclasses import dataclass

from lottery_system.config import RESULT_FILE_PREFIX
from lottery_system.models import Prize, User

UNKNOWN_LEVEL = 999

_ORDINAL_LEVELS = {
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
_LEVEL_PATTERN = re.compile(
    r"^\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+prize",
    re.IGNORECASE,
)


def get_prize_level(prize: Prize) -> int:
    """Derive the prize level from its name (e.g. 'First Prize - ...' -> 1).

    Prizes without a recognised ordinal are ranked after all ordinal prizes.
    """
    match = _LEVEL_PATTERN.match(prize.name)
    if not match:
        return UNKNOWN_LEVEL
    return _ORDINAL_LEVELS[match.group(1).lower()]


@dataclass
class Winner:
    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    win_time: datetime.datetime


class ResultManager:
    """Keeps all winners in winning order and produces summaries/exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._counter: int = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._counter += 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=get_prize_level(prize),
            winning_order=self._counter,
            win_time=datetime.datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low),
        then by prize sequence; winners within a prize ordered by winning time."""
        ordered = sorted(enumerate(prizes), key=lambda item: (get_prize_level(item[1]), item[0]))
        result: dict[str, list[Winner]] = {}
        for _, prize in ordered:
            winners = sorted(
                (w for w in self._winners if w.prize_name == prize.name),
                key=lambda w: w.winning_order,
            )
            result[prize.name] = winners
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list as CSV into awards_result_YYYYMMDD.txt in the current directory."""
        grouped = self.get_winners_by_prize(prizes)
        file_name = f"{RESULT_FILE_PREFIX}{datetime.date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["Prize Level", "Prize Name", "Winning Order", "Name", "Department", "Win Time"]
                )
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        level = "" if winner.prize_level == UNKNOWN_LEVEL else winner.prize_level
                        writer.writerow(
                            [
                                level,
                                prize_name,
                                winner.winning_order,
                                winner.user.name,
                                winner.user.department,
                                winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
