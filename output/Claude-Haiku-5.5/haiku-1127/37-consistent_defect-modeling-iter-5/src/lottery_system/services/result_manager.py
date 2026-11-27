"""Winner records, grouped results and CSV export."""
import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize: Prize
    winning_order: int = 0
    winning_time: datetime = field(default_factory=datetime.now)


def _sorted_prizes(prizes):
    """Prizes ordered from highest level to lowest (stable for equal levels)."""
    return sorted(prizes, key=lambda prize: prize.level, reverse=True)


class ResultManager:
    def __init__(self):
        self._winners = []

    def add_winner(self, user, prize):
        winner = Winner(user=user, prize=prize,
                        winning_order=len(self._winners) + 1,
                        winning_time=datetime.now())
        self._winners.append(winner)
        return winner

    def get_winners(self):
        return list(self._winners)

    def get_winners_by_prize(self, prizes):
        """Return {prize name: [Winner, ...]} ordered by prize level (high to low),
        with winners within each prize in winning order."""
        result = {}
        for prize in _sorted_prizes(prizes):
            result[prize.name] = [w for w in self._winners if w.prize.name == prize.name]
        return result

    def export_to_csv(self, prizes):
        """Export the winner list to awards_result_YYYYMMDD.txt in the current directory."""
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for winner in winners:
                        writer.writerow([
                            winner.user.name,
                            winner.user.department,
                            prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
