"""Winner records, summaries and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order

    @property
    def prize_name(self) -> str:
        return self.prize.name if isinstance(self.prize, Prize) else str(self.prize)

    def __repr__(self):
        return f"Winner({self.user!r}, {self.prize_name!r})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def add_winner(self, user, prize):
        if any(w.user.name == user.name for w in self.winners):
            return None
        w = Winner(user, prize, datetime.now(), len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        indexed = list(enumerate(prizes or []))
        indexed.sort(key=lambda t: (t[1].level, t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, p in indexed:
            result.setdefault(p.name, [])
        for w in sorted(self.winners, key=lambda x: (x.time, x.order)):
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winning results to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for pname, winners in self.get_winners_by_prize(prizes).items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, pname,
                                         w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
