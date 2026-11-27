"""Winner recording, summary and CSV export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import User


@dataclass
class Winner:
    user: User
    prize_name: str
    prize_level: int
    winning_order: int
    win_time: datetime

    @property
    def name(self):
        return self.user.name

    @property
    def department(self):
        return self.user.department


class ResultManager:
    """Keeps the winner list and exports it."""

    def __init__(self):
        self._winners = []
        self._counter = 0

    def add_winner(self, user, prize):
        self._counter += 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=getattr(prize, "level", 99),
            winning_order=self._counter,
            win_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self):
        return list(self._winners)

    def get_ordered_winners(self, prizes=None):
        """Winners sorted by prize level (high to low), then winning order."""
        return sorted(self._winners, key=lambda w: (w.prize_level, w.winning_order))

    def get_winners_by_prize(self, prizes):
        """Return {prize name: [Winner, ...]} in the order of the given prizes."""
        grouped = {prize.name: [] for prize in prizes}
        for winner in sorted(self._winners, key=lambda w: w.winning_order):
            grouped.setdefault(winner.prize_name, []).append(winner)
        return grouped

    def export_to_csv(self, prizes):
        """Export the full winner list to current_dir/awards_result_YYYYMMDD.txt."""
        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        ordered = self.get_ordered_winners(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in ordered:
                    writer.writerow(
                        [
                            winner.name,
                            winner.department,
                            winner.prize_name,
                            winner.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
