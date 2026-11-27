"""Winner recording, ordering and CSV export."""

from __future__ import annotations

import csv
import datetime
import os
import re
from dataclasses import dataclass

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
_LEVEL_PATTERN = re.compile(r"^\s*([A-Za-z]+)\b")
_UNRANKED = 99


def prize_level(prize_name: str) -> int:
    """Return the prize rank derived from its name (1 = highest).

    Names without a recognised ordinal word (e.g. "Custom Gift") rank last.
    """
    match = _LEVEL_PATTERN.match(prize_name or "")
    if not match:
        return _UNRANKED
    return _LEVEL_WORDS.get(match.group(1).lower(), _UNRANKED)


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int
    won_at: datetime.datetime


class ResultManager:
    """Stores winners and produces ordered results."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._sequence = 0

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record that ``user`` won ``prize``."""
        self._sequence += 1
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        self._winners.append(
            Winner(
                user=user,
                prize_name=prize_name,
                sequence=self._sequence,
                won_at=datetime.datetime.now(),
            )
        )

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return sorted(self._winners, key=lambda w: w.sequence)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map each prize name to its winners in winning-time order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            winners = [w for w in self._winners if w.prize_name == prize.name]
            result[prize.name] = sorted(winners, key=lambda w: w.sequence)
        return result

    def get_ordered_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners ordered by prize level (high to low), then winning time."""
        indexed = sorted(
            enumerate(prizes),
            key=lambda item: (prize_level(item[1].name), item[0]),
        )
        by_prize = self.get_winners_by_prize(prizes)
        ordered: list[Winner] = []
        for _, prize in indexed:
            ordered.extend(by_prize.get(prize.name, []))
        return ordered

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt."""
        date_text = datetime.datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")
        rows = self.get_ordered_winners(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
