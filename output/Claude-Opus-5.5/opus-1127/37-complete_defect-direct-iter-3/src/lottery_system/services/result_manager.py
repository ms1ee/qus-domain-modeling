"""Result storage and export."""
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize: Prize
    order: int = 0


def _prize_name(p) -> str:
    return p.name if hasattr(p, "name") else str(p)


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes or []:
            result[_prize_name(p)] = []
        for w in self.winners:
            result.setdefault(_prize_name(w.prize), []).append(w)
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for pname, ws in grouped.items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, pname])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
