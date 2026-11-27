import datetime
import os


class Winner:
    def __init__(self, user, prize_name):
        self.user = user
        self.prize_name = prize_name


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, getattr(prize, "name", prize))
        self.winners.append(w)
        return w

    def get_winners_by_prize(self, prizes):
        res = {}
        for p in prizes:
            res[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return res

    def export_to_csv(self, prizes):
        fname = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), fname)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for p in prizes:
                    for w in grouped[p.name]:
                        f.write(f"{w.user.name},{w.user.department},{w.prize_name}\n")
            return True, f"Results successfully exported to {path}"
        except OSError as e:
            return False, f"Export failed: {e}"
