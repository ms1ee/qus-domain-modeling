"""Winner recording, ordering, and CSV export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User

_LEVEL_PATTERN = re.compile(r"\b(first|second|third)\s+prize\b", re.IGNORECASE)
_LEVELS = {"first": 1, "second": 2, "third": 3}
_UNRANKED_LEVEL = 99


def prize_level(prize_name: str) -> int:
    """Return the numeric level of a prize (1 = highest). Unranked prizes return 99."""
    match = _LEVEL_PATTERN.search(prize_name or "")
    if not match:
        return _UNRANKED_LEVEL
    return _LEVELS[match.group(1).lower()]


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int  # global winning order (1-based)


class ResultManager:
    """Stores winners and produces ordered results and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        winner = Winner(user=user, prize_name=prize_name, sequence=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, each list in winning order."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def get_sorted_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners sorted by prize level (high to low), then prize order, then winning order."""
        order = {prize.name: index for index, prize in enumerate(prizes)}
        fallback_index = len(order)
        return sorted(
            self._winners,
            key=lambda w: (
                prize_level(w.prize_name),
                order.get(w.prize_name, fallback_index),
                w.sequence,
            ),
        )

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        winners = self.get_sorted_winners(prizes)
        if not winners:
            return False, "No winners to export."

        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in winners:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.sequence,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
