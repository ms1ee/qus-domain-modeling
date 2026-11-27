import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize, time=None):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        self.winners.append(Winner(user, prize))

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = sorted(
                [w for w in self.winners if w.prize.name == p.name],
                key=lambda w: w.time,
            )
        return result

    def export_to_csv(self, prizes):
        try:
            path = os.path.join(
                os.getcwd(), f"awards_result_{datetime.now():%Y%m%d}.txt")
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for p in prizes:
                    for w in grouped.get(p.name, []):
                        f.write(f"{w.user.name},{w.user.department},{p.name},"
                                f"{w.time:%Y-%m-%d %H:%M:%S}\n")
            return True, f"Results successfully exported to {path}"
        except OSError as e:
            return False, f"Export failed: {e}"
