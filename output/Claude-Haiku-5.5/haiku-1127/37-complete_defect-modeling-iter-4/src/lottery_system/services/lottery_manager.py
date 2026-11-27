import random

from lottery_system.models import Prize, User


CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"


def _norm(value) -> str:
    return (value or "").strip().casefold()


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Applies the lottery rule engine and performs draws."""

    def __init__(self, users):
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self._winners: list[User] = []
        # Results (True = winner belongs to Cheng Ru group) of the last two
        # draws made by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        return list(self._winners)

    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def _base_pool(self) -> list[User]:
        return [u for u in self._users if u.name not in self._winner_names]

    def _is_cheng_ru_fallback_active(self) -> bool:
        return (
            len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        base = self._base_pool()
        drawer = _norm(prize.associated_drawer)

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members,
        # overriding avoidance groups.
        if drawer == _norm(MA_JIAQI) and self._is_cheng_ru_fallback_active():
            return [u for u in base if _is_cheng_ru(u)]

        # Special rule: Li Bin only filters previous winners.
        if drawer == _norm(LI_BIN):
            return base

        avoid = {_norm(g) for g in prize.avoid_groups}
        if not avoid:
            return base
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rule(self, prize: Prize) -> str:
        parts = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        parts.append("Previous winners are excluded")
        drawer = _norm(prize.associated_drawer)
        if drawer == _norm(LI_BIN):
            parts.append("Special rule: only previous winners are filtered (avoidance groups not applied)")
        elif drawer == _norm(MA_JIAQI) and self._is_cheng_ru_fallback_active():
            parts.append("Cheng Ru group protection: only Cheng Ru Group members are eligible")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(parts)

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._record_winner(winner)

        drawer = _norm(prize.associated_drawer)
        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            self.last_two_draw_results.append(_is_cheng_ru(winner))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner

    def _record_winner(self, user: User) -> None:
        if user.name in self._winner_names:
            raise ValueError(f"{user.name} has already won a prize.")
        self._winner_names.add(user.name)
        self._winners.append(user)
