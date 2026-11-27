import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, time=None, order=0):
        self.user = user
        self.prize_name = prize_name
        self.time = time or datetime.now()
        self.order = order


def _level(name):
    low = name.lower()
    for i, k in enumerate(("first", "second", "third")):
        if low.startswith(k):
            return i
    return 99


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        self.winners.append(Winner(user, prize.name, datetime.now(), len(self.winners) + 1))

    def get_winners_by_prize(self, prizes):
        names = []
        for p in prizes:
            if p.name not in names:
                names.append(p.name)
        names.sort(key=_level)
        result = {}
        for n in names:
            ws = [w for w in self.winners if w.prize_name == n]
            ws.sort(key=lambda w: w.order)
            result[n] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for n, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{n},"
                                f"{w.time:%Y-%m-%d %H:%M:%S}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
