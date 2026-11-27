import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name="", time=None):
        self.user = user
        self.prize_name = prize_name
        self.time = time or datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return result

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for pname, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{pname},"
                                f"{w.time:%Y-%m-%d %H:%M:%S}\n")
            return True, f"Results successfully exported to {path}"
        except Exception as e:
            return False, f"Export failed: {e}"
