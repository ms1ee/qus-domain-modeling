import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, win_time=None):
        self.user = user
        self.prize_name = prize_name
        self.win_time = win_time or datetime.now()


def _level(name):
    n = name.lower()
    for i, k in enumerate(("first", "second", "third"), 1):
        if k in n:
            return i
    return 99


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        names = []
        for p in prizes:
            if p.name not in names:
                names.append(p.name)
        names.sort(key=_level)
        return {n: [w for w in self.winners if w.prize_name == n] for n in names}

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for n, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{n},"
                                f"{w.win_time:%Y-%m-%d %H:%M:%S}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
