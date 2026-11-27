import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, order=0, time=None):
        self.user = user
        self.prize_name = prize_name
        self.order = order
        self.time = time or datetime.now()


def _level(name):
    n = name.lower()
    for i, k in enumerate(("special", "first", "second", "third")):
        if k in n:
            return i
    return 99


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        idx = list(enumerate(prizes))
        idx.sort(key=lambda t: (_level(t[1].name), t[0]))
        result = {}
        for _, p in idx:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return result

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize,WinningOrder,WinningTime\n")
                for pname, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{pname},{w.order},"
                                f"{w.time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
