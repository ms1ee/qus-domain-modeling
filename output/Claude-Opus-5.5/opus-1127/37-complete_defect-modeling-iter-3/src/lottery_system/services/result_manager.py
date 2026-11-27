"""Result management and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List


class Winner:
    def __init__(self, user, prize, order: int):
        self.user = user
        self.prize = prize
        self.win_order = order
        self.timestamp = datetime.now()

    def __repr__(self) -> str:
        return f"Winner({self.user.name!r}, {self.prize.name!r}, #{self.win_order})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self.export_format = "csv"
        self.export_path = None

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            result.setdefault(p.name, [])
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
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        self.export_path = path
        return True, f"Results successfully exported to {path}"
