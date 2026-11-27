import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name="", time=None, order=0):
        self.user = user
        self.prize_name = prize_name
        self.time = time or datetime.now()
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        name = getattr(prize, "name", prize)
        self.winners.append(Winner(user, name, datetime.now(), len(self.winners) + 1))

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            name = getattr(p, "name", p)
            result[name] = sorted((w for w in self.winners if w.prize_name == name),
                                  key=lambda w: w.order)
        return result

    def export_to_csv(self, prizes):
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now():%Y%m%d}.txt")
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for name, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name},"
                                f"{w.time:%Y-%m-%d %H:%M:%S}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
