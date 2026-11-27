import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, order=0):
        self.user = user
        self.prize_name = prize_name
        self.order = order
        self.time = datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize.name, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = sorted(
                (w for w in self.winners if w.prize_name == p.name),
                key=lambda w: w.order)
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
