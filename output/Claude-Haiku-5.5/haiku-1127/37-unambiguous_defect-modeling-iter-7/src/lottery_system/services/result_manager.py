"""Winner recording, summarizing and CSV export."""

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int
    winning_time: datetime

    @property
    def prize_name(self):
        return self.prize.name

    @property
    def prize_level(self):
        return self.prize.level


class ResultManager:
    """Keeps the winner list and produces summaries and exports."""

    def __init__(self):
        self._winners = []
        self._counter = 0

    def add_winner(self, user, prize):
        """Record a winner for a prize and return the Winner record."""
        self._counter += 1
        winner = Winner(user, prize, self._counter, datetime.now())
        self._winners.append(winner)
        return winner

    def get_all_winners(self):
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes):
        """Return {prize name: [Winner, ...]} sorted by winning order."""
        result = {}
        for prize in prizes:
            matched = [winner for winner in self._winners if winner.prize.name == prize.name]
            result[prize.name] = sorted(matched, key=lambda winner: winner.winning_order)
        return result

    def get_ordered_winners(self, prizes):
        """Return winners ordered by prize level (high to low), then winning order."""
        grouped = self.get_winners_by_prize(prizes)
        ordered = []
        for prize in sorted(prizes, key=lambda item: item.level):
            ordered.extend(grouped.get(prize.name, []))
        return ordered

    def export_to_csv(self, prizes):
        """Export the ordered winner list to current_dir/awards_result_YYYYMMDD.txt.

        Returns (success, message).
        """
        try:
            filename = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
            path = os.path.join(os.getcwd(), filename)
            rows = self.get_ordered_winners(prizes)
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["Prize Level", "Prize Name", "Winning Order", "Name", "Department", "Winning Time"]
                )
                for winner in rows:
                    writer.writerow(
                        [
                            winner.prize_level,
                            winner.prize_name,
                            winner.winning_order,
                            winner.user.name,
                            winner.user.department,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
