"""Winner recording, grouping and CSV export."""

import csv
import datetime
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    winning_order: int
    win_time: datetime.datetime


class ResultManager:
    """Keeps all winning records of the current lottery."""

    def __init__(self):
        self._winners: List[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize."""
        record = Winner(
            user=user,
            prize_name=prize.name,
            winning_order=len(self._winners) + 1,
            win_time=datetime.datetime.now(),
        )
        self._winners.append(record)
        return record

    def get_winners(self) -> List[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        """Group winners by prize name, keeping the order of the given prizes."""
        grouped: Dict[str, List[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        """Export the complete winner list as CSV into the current directory."""
        date_text = datetime.datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")

        grouped = self.get_winners_by_prize(prizes)
        ordered: List[Winner] = []
        for prize in prizes:
            ordered.extend(grouped.get(prize.name, []))
        known_names = {prize.name for prize in prizes}
        ordered.extend(w for w in self._winners if w.prize_name not in known_names)

        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Winning Order", "Name", "Department", "Prize"])
                for winner in ordered:
                    writer.writerow([
                        winner.winning_order,
                        winner.user.name,
                        winner.user.department,
                        winner.prize_name,
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"

        return True, f"Result successfully exported to {path}"
