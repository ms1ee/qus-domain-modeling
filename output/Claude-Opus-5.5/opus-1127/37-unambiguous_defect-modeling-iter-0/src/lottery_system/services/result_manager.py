"""Winner recording, summary, and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import prize_level_rank


class Winner:
    def __init__(self, user, prize_name: str, win_time: datetime, order: int):
        self.user = user
        self.prize_name = prize_name
        self.prize = prize_name
        self.win_time = win_time
        self.order = order

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._counter = 0

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self._counter += 1
        self.winners.append(Winner(user, _prize_name(prize), datetime.now(), self._counter))
        return True

    def get_round_winners(self, prize) -> List[Winner]:
        name = _prize_name(prize)
        return [w for w in self.winners if w.prize_name == name]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names = []
        for p in prizes or []:
            n = _prize_name(p)
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
            ws.sort(key=lambda w: (w.win_time, w.order))
            result[n] = ws
        return result

    def clear(self) -> None:
        self.winners = []
        self._counter = 0

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["No.", "Name", "Department", "Prize", "Winning Time"])
                idx = 0
                for prize_name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        idx += 1
                        writer.writerow([idx, w.user.name, w.user.department, prize_name,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
