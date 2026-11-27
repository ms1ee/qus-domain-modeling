"""Winner records, summary and export."""
import csv
import os
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import prize_level, UNKNOWN_LEVEL

TIME_FMT = "%Y-%m-%d %H:%M:%S"


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order

    @property
    def prize_name(self):
        return self.prize.name if hasattr(self.prize, "name") else str(self.prize)

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._counter = 0

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize):
        if self.has_won(user):
            return None
        self._counter += 1
        w = Winner(user, prize, datetime.now(), self._counter)
        self.winners.append(w)
        return w

    def _sorted_prizes(self, prizes):
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in self._sorted_prizes(prizes):
            result[p.name] = sorted(
                [w for w in self.winners if w.prize_name == p.name],
                key=lambda w: (w.time, w.order))
        # winners for prizes not in the list
        known = set(result)
        for w in sorted(self.winners, key=lambda w: (w.time, w.order)):
            if w.prize_name not in known:
                result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, ws in grouped.items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, prize_name,
                                         w.time.strftime(TIME_FMT)])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
