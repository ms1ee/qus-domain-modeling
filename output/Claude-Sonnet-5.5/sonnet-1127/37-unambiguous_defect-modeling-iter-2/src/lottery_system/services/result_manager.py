import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize=None, order=0):
        self.user = user
        self.prize = prize
        self.order = order
        self.time = datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners
                              if w.prize is not None and w.prize.name == p.name]
        return result

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for pname, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{pname}\n")
            return True, f"Results successfully exported to {path}"
        except OSError as e:
            return False, f"Export failed: {e}"
