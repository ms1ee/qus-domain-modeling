"""Lottery process control and rule engine."""

import random

SPECIAL_DRAWER = "Li Bin"
FALLBACK_TRIGGERS = ["Chen Qixian", "Jin Duo"]
FALLBACK_TARGET = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm_group(name):
    s = str(name or "").strip().lower().replace(" ", "")
    if s.endswith("group"):
        s = s[: -len("group")]
    return s


def _same_group(a, b):
    return _norm_group(a) == _norm_group(b)


def _norm_person(name):
    return " ".join(str(name or "").split()).lower()


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryManager:
    """Executes draws while applying the rule engine."""

    def __init__(self, users, result_manager=None, rng=None):
        self.users = list(users)
        self.result_manager = result_manager
        self.rng = rng or random.Random()
        self.winner_names = set()
        self.winners = []  # list of (user, prize)
        self.last_two_draw_results = []

    # -------------------------------------------------------------- rule engine
    def is_winner(self, user):
        return user.name in self.winner_names

    def is_fallback_active(self, prize):
        if _norm_person(prize.associated_drawer) != _norm_person(FALLBACK_TARGET):
            return False
        last = self.last_two_draw_results[-2:]
        return len(last) >= 2 and not any(last)

    def _get_eligible_pool(self, prize):
        not_won = [u for u in self.users if not self.is_winner(u)]
        if self.is_fallback_active(prize):
            return [u for u in not_won if _same_group(u.department, PROTECTED_GROUP)]
        if _norm_person(prize.associated_drawer) == _norm_person(SPECIAL_DRAWER):
            return not_won
        avoid = [_norm_group(g) for g in prize.avoid_groups]
        return [u for u in not_won if _norm_group(u.department) not in avoid]

    def describe_rules(self, prize):
        drawer = prize.associated_drawer or "None"
        parts = [f"Lottery person: {drawer}", "Previous winners excluded"]
        if self.is_fallback_active(prize):
            parts.append(
                f"FALLBACK ACTIVE: pool limited to '{PROTECTED_GROUP}' members "
                f"(previous rounds by {' and '.join(FALLBACK_TRIGGERS)} had no {PROTECTED_GROUP} winners)"
            )
        elif _norm_person(prize.associated_drawer) == _norm_person(SPECIAL_DRAWER):
            parts.append(f"Special lottery person {SPECIAL_DRAWER}: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        return "; ".join(parts)

    def record_round_result(self, prize, round_winners):
        drawer = _norm_person(prize.associated_drawer)
        if drawer in [_norm_person(p) for p in FALLBACK_TRIGGERS]:
            hit = any(_same_group(u.department, PROTECTED_GROUP) for u in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm_person(FALLBACK_TARGET):
            self.last_two_draw_results = []

    # ----------------------------------------------------------------- drawing
    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winner_names.add(user.name)
        self.winners.append((user, prize))
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def _prompt_control(self, input_func, output_func):
        """Returns 'draw' or 'terminate'."""
        paused = False
        while True:
            prompt = ("[Paused] type 'continue' to resume or 'terminate' to end round: "
                      if paused else
                      "Press Enter to draw (or type 'pause' / 'terminate'): ")
            try:
                cmd = input_func(prompt).strip().lower()
            except EOFError:
                return "draw"
            if cmd == "terminate":
                return "terminate"
            if paused:
                if cmd == "continue":
                    output_func("Lottery resumed.")
                    return "draw"
                output_func("Lottery is paused.")
                continue
            if cmd == "pause":
                paused = True
                output_func("Lottery paused.")
                continue
            if cmd in ("", "continue", "draw"):
                return "draw"
            output_func("Unknown command.")

    def run_round(self, prize, round_number=1, input_func=input, output_func=print,
                  interactive=True):
        output_func("=" * 60)
        output_func(f"Round {round_number}: {prize.name} | Quantity: {prize.quantity}")
        output_func(f"Rules: {self.describe_rules(prize)}")
        output_func("=" * 60)
        round_winners = []
        for i in range(prize.quantity):
            if interactive:
                if self._prompt_control(input_func, output_func) == "terminate":
                    output_func("Current round terminated and skipped.")
                    break
            output_func(f"Currently drawing the {ordinal(i + 1)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output_func("No eligible participants remain for this prize. Round ended.")
                break
            output_func(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            round_winners.append(user)
        self.record_round_result(prize, round_winners)
        output_func(f"--- Round {round_number} results ({prize.name}) ---")
        if round_winners:
            for n, u in enumerate(round_winners, 1):
                output_func(f"  {n}. {u.name} ({u.department})")
        else:
            output_func("  No winners in this round.")
        return round_winners
