import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, win_time=None):
        self.user = user
        self.prize_name = prize_name
        self.win_time = win_time or datetime.now()


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        name = getattr(prize, "name", prize)
        self.winners.append(Winner(user, name))

    def get_winners_by_prize(self, prizes):
        res = {}
        for p in prizes:
            res[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return res

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        rows = [w for lst in grouped.values() for w in lst]
        if not rows:
            return False, "No winners to export"
        fname = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), fname)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize Name,Winning Time\n")
                for w in rows:
                    f.write(f"{w.user.name},{w.user.department},{w.prize_name},"
                            f"{w.win_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
