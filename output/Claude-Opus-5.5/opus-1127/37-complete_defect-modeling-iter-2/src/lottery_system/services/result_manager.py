"""Result recording, display and export."""

from __future__ import annotations

import csv
import datetime
import os
from typing import Dict, List, Tuple


class Winner:
    """A winning record."""

    def __init__(self, user, prize, order: int = 0):
        self.user = user
        self.prize = prize
        self.prize_name = getattr(prize, "name", str(prize))
        self.order = order

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"

    def __str__(self):
        return (
            f"Congratulations {self.user.name} ({self.user.department}) "
            f"for winning {self.prize_name}"
        )


class ResultManager:
    """Maintains the winner list."""

    def __init__(self):
        self.winners: List[Winner] = []

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_won(user):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def get_all_winners(self) -> List[Winner]:
        return list(self.winners)

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            pname = getattr(p, "name", str(p))
            result[pname] = []
        for w in self.winners:
            if w.prize_name in result:
                result[w.prize_name].append(w)
            else:
                result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes, path=None) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        if path is None:
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            path = os.path.join(os.getcwd(), f"awards_result_{date_str}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for pname, winners in grouped.items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, pname])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
