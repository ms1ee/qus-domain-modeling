"""Winner recording, ordering, and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from ..models import Prize, User, normalize_text


def prize_level(prize_name: str) -> int:
    """Return the level rank of a prize (1 = highest). Unknown levels rank last."""
    name = normalize_text(prize_name)
    if "first" in name:
        return 1
    if "second" in name:
        return 2
    if "third" in name:
        return 3
    return 99


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int
    won_at: datetime


class ResultManager:
    """Keeps all winning records of a lottery session."""

    def __init__(self):
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize) -> Winner:
        """Record a winner for a prize (Prize object or prize name)."""
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        record = Winner(
            user=user,
            prize_name=prize_name,
            sequence=len(self._winners) + 1,
            won_at=datetime.now(),
        )
        self._winners.append(record)
        return record

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Map each prize name to its winners, in winning order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            name = prize.name if isinstance(prize, Prize) else str(prize)
            result[name] = sorted(
                (w for w in self._winners if w.prize_name == name),
                key=lambda w: w.sequence,
            )
        return result

    def ordered_prizes(self, prizes) -> list[Prize]:
        """Prizes sorted by level from high to low (stable for equal levels)."""
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda item: (prize_level(item[1].name), item[0]))
        return [prize for _, prize in indexed]

    def get_ordered_winners(self, prizes) -> list[Winner]:
        """Winners ordered by prize level (high to low), then winning time."""
        ordered: list[Winner] = []
        winners_map = self.get_winners_by_prize(self.ordered_prizes(prizes))
        for prize in self.ordered_prizes(prizes):
            ordered.extend(winners_map.get(prize.name, []))
        return ordered

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        date_text = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self.get_ordered_winners(prizes):
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize_name,
                        winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
