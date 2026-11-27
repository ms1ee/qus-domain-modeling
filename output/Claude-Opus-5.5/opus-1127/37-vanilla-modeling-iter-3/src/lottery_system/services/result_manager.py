"""Winner records, summary and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import prize_level_rank


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order

    @property
    def prize_name(self) -> str:
        return self.prize.name if hasattr(self.prize, "name") else str(self.prize)

    def __repr__(self):
        return f"Winner({self.user.name}, {self.user.department}, {self.prize_name})"


def _pname(p) -> str:
    return p.name if hasattr(p, "name") else str(p)


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def add_winner(self, user, prize):
        w = Winner(user, prize, datetime.now(), len(self.winners) + 1)
        self.winners.append(w)
        return w

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names = []
        for p in prizes or []:
            n = _pname(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        indexed = list(enumerate(names))
        indexed.sort(key=lambda t: (prize_level_rank(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, n in indexed:
            ws = [w for w in self.winners if w.prize_name == n]
            ws.sort(key=lambda w: (w.time, w.order))
            result[n] = ws
        return result

    def export_to_csv(self, prizes, directory=None):
        if not self.winners:
            return False, "No winners to export"
        directory = directory or os.getcwd()
        path = os.path.join(directory, f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for pname, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, pname,
                                         w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
