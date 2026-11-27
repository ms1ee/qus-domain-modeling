"""Result storage, display and export."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

from lottery_system.models import User


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


@dataclass
class Winner:
    user: User
    prize: Any

    @property
    def prize_name(self) -> str:
        return _prize_name(self.prize)


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes or []:
            result.setdefault(_prize_name(p), [])
        for w in self.winners:
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes, path=None) -> Tuple[bool, str]:
        if path is None:
            fname = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
            path = os.path.join(os.getcwd(), fname)
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
