"""Result management and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User


class Winner:
    """A winning record."""

    def __init__(self, user: User, prize: Prize, draw_order: int):
        self.user = user
        self.prize = prize
        self.draw_order = draw_order
        self.win_time = datetime.now()

    def __repr__(self) -> str:
        return f"Winner(user={self.user!r}, prize={self.prize.name!r}, order={self.draw_order})"


class ResultManager:
    """Keeps the winner list and exports it."""

    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def count_for_prize(self, prize) -> int:
        return sum(1 for w in self.winners if w.prize.name == prize.name)

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {p.name: [] for p in prizes}
        for w in self.winners:
            if w.prize.name in result:
                result[w.prize.name].append(w)
        return result

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        rows = [w for p in prizes for w in grouped.get(p.name, [])]
        # include winners whose prize may not be in the list anymore
        listed = set(id(w) for w in rows)
        rows += [w for w in self.winners if id(w) not in listed]
        if not rows:
            return False, "No winners to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for w in rows:
                    writer.writerow([w.user.name, w.user.department, w.prize.name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
