"""Result storage, display grouping and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User


class Winner:
    def __init__(self, user: User, prize: Prize, order: int) -> None:
        self.user = user
        self.prize = prize
        self.order = order

    def __repr__(self) -> str:
        return f"Winner({self.order}, {self.user.name}, {self.user.department}, {self.prize.name})"


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        w = Winner(user, prize, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {p.name: [] for p in prizes}
        for w in self.winners:
            result.setdefault(w.prize.name, []).append(w)
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for prize_name, ws in grouped.items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, prize_name])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
