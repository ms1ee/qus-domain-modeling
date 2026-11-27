"""Result management and export."""
import csv
import os
from datetime import datetime
from typing import Dict, List, Optional


def prize_level(name: str) -> int:
    n = (name or "").lower()
    for key, lvl in (("special", 0), ("grand", 0), ("first", 1), ("second", 2),
                     ("third", 3), ("fourth", 4), ("fifth", 5)):
        if key in n:
            return lvl
    return 99


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order

    @property
    def prize_name(self):
        return getattr(self.prize, "name", str(self.prize))

    def __repr__(self):
        return f"Winner({self.user.name}, {self.user.department}, {self.prize_name})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def has_winner(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_winner(user):
            return False
        self.winners.append(Winner(user, prize, datetime.now(), len(self.winners) + 1))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names = []
        for p in prizes or []:
            nm = getattr(p, "name", str(p))
            if nm not in names:
                names.append(nm)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        ordered = sorted(enumerate(names), key=lambda t: (prize_level(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, nm in ordered:
            ws = [w for w in self.winners if w.prize_name == nm]
            ws.sort(key=lambda w: (w.time, w.order))
            result[nm] = ws
        return result

    def export_to_csv(self, prizes, directory: Optional[str] = None):
        directory = directory or os.getcwd()
        path = os.path.join(directory, f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for nm, ws in grouped.items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, nm,
                                         w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
