"""Winner recording, ordering, and CSV/txt export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, normalize_text

_LEVEL_KEYWORDS = (
    ("grand", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
)


def prize_level_rank(prize_name: str) -> int | None:
    """Return the level rank of a prize (smaller is higher), or None if unknown."""
    lowered = prize_name.casefold()
    for keyword, rank in _LEVEL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return rank
    return None


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    win_order: int
    won_at: datetime


class ResultManager:
    """Maintains the real-time winner list and exports results."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._winner_keys: set[str] = set()

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        """Record a winner. Raises ValueError if the person already won."""
        key = normalize_text(user.name)
        if key in self._winner_keys:
            raise ValueError(f"{user.name} has already won a prize.")
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        winner = Winner(
            user=user,
            prize_name=prize_name,
            win_order=len(self._winners) + 1,
            won_at=datetime.now(),
        )
        self._winners.append(winner)
        self._winner_keys.add(key)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name.

        Prizes are ordered from high level to low level; within a prize,
        winners are in winning time order.
        """
        ordered = self._sort_prizes(prizes)
        result: dict[str, list[Winner]] = {prize.name: [] for prize in ordered}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    @staticmethod
    def _sort_prizes(prizes: list[Prize]) -> list[Prize]:
        def sort_key(item: tuple[int, Prize]) -> tuple[int, int]:
            index, prize = item
            rank = prize_level_rank(prize.name)
            return (rank if rank is not None else 1000, index)

        return [prize for _, prize in sorted(enumerate(prizes), key=sort_key)]

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow(
                            [
                                winner.user.name,
                                winner.user.department,
                                prize_name,
                                winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
