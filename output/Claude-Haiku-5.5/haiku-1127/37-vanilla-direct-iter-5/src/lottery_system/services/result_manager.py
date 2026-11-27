import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int
    timestamp: str


_ORDINAL_RANKS = {
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

_UNRANKED = 10_000


def prize_level_rank(prize_name: str) -> int:
    """Lower rank means higher prize level. Unranked prizes come last."""
    match = re.search(
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
        prize_name,
        re.IGNORECASE,
    )
    if match:
        return _ORDINAL_RANKS[match.group(1).lower()]
    match = re.search(r"\b(\d+)(st|nd|rd|th)\b", prize_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return _UNRANKED


class ResultManager:
    """Stores winners and produces ordered results and exports."""

    def __init__(self):
        self._winners: list[Winner] = []
        self._sequence = 0

    def add_winner(self, user, prize) -> Winner:
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        self._sequence += 1
        winner = Winner(
            user=user,
            prize_name=prize_name,
            sequence=self._sequence,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            name = prize.name if isinstance(prize, Prize) else str(prize)
            result.setdefault(name, [])
        for winner in self._winners:
            result.setdefault(winner.prize_name, []).append(winner)
        return result

    def get_sorted_winners(self, prizes) -> list[Winner]:
        """Winners sorted by prize level (high to low), then by winning order."""
        names = [p.name if isinstance(p, Prize) else str(p) for p in prizes]
        index_map = {name: idx for idx, name in enumerate(names)}

        def key(winner: Winner):
            return (
                prize_level_rank(winner.prize_name),
                index_map.get(winner.prize_name, len(names)),
                winner.sequence,
            )

        return sorted(self._winners, key=key)

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self.get_sorted_winners(prizes):
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.timestamp,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
