"""Winner records, summaries and export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User


@dataclass
class Winner:
    user: User
    prize: Prize
    win_time: datetime = field(default_factory=datetime.now)
    order: int = 0

    @property
    def prize_name(self) -> str:
        return self.prize.name if isinstance(self.prize, Prize) else str(self.prize)


def _sorted_prizes(prizes) -> List[Prize]:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda t: (t[1].level is None,
                                t[1].level if t[1].level is not None else 0, t[0]))
    return [p for _, p in indexed]


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._counter = 0

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def add_winner(self, user: User, prize: Prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self._counter += 1
        self.winners.append(Winner(user, prize, datetime.now(), self._counter))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in _sorted_prizes(prizes):
            ws = [w for w in self.winners if w.prize_name == prize.name]
            ws.sort(key=lambda w: (w.win_time, w.order))
            result[prize.name] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Prize", "Name", "Department", "Winning Order", "Win Time"])
                for prize_name, ws in grouped.items():
                    for w in ws:
                        writer.writerow([prize_name, w.user.name, w.user.department, w.order,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
