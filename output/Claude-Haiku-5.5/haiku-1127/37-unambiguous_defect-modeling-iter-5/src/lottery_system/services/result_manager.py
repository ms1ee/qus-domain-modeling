"""Winner recording, ranking and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.constants import LEVEL_CUSTOM
from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str = ""
    prize_level: int = LEVEL_CUSTOM
    winning_order: int = 0
    winning_time: datetime = field(default_factory=datetime.now)


class ResultManager:
    """Keeps the winner history and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the given prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize.level,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name to its winners (in winning order), following the prize order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def get_ranked_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Winners sorted by prize level (high to low), then by winning order within a prize."""
        indexed = sorted(enumerate(prizes), key=lambda item: (item[1].level, item[0]))
        ranked: list[Winner] = []
        seen: set[str] = set()
        for _, prize in indexed:
            if prize.name in seen:
                continue
            seen.add(prize.name)
            ranked.extend(w for w in self._winners if w.prize_name == prize.name)
        return ranked

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the ranked winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        ranked = self.get_ranked_winners(prizes)
        if not ranked:
            return False, "No winners to export."
        stamp = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{stamp}.txt")
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["Winning Order", "Prize Name", "Prize Level", "Name", "Department", "Winning Time"]
                )
                for winner in ranked:
                    writer.writerow(
                        [
                            winner.winning_order,
                            winner.prize_name,
                            winner.prize_level,
                            winner.user.name,
                            winner.user.department,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
