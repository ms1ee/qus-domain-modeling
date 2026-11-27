import datetime


class Winner:
    def __init__(self, user, prize_name, order=0):
        self.user = user
        self.prize_name = prize_name
        self.order = order
        self.time = datetime.datetime.now()


def _level(name):
    low = name.lower()
    for i, k in enumerate(("special", "first", "second", "third")):
        if low.startswith(k):
            return i
    return 99


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        self.winners.append(Winner(user, prize.name, len(self.winners) + 1))

    def get_winners_by_prize(self, prizes):
        ordered = sorted(prizes, key=lambda p: _level(p.name))
        result = {}
        for p in ordered:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for pname, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{pname}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
