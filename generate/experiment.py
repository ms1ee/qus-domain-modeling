"""Shared validation of experiment conditions before any model work."""

DEFAULT_SEED_BASE = 42
DEFAULT_FEEDBACK_LEVEL = 1
# llama.cpp reserves UINT32_MAX for a fresh random seed, not a fixed seed.
MAX_SEED = 2**32 - 2


def validate_feedback_level(level):
    if type(level) is not int or level not in (1, 2, 3):
        raise ValueError('feedback_level must be 1, 2, or 3')
    return level


def iteration_seed(base, index):
    if (type(base) is not int or type(index) is not int or index < 0
            or not 0 <= base <= MAX_SEED or base + index > MAX_SEED):
        raise ValueError('seed base and every repetition seed must be integers between 0 and 4294967294; '
                         '4294967295 is reserved for random seeding')
    return base + index


def seed_schedule(base, count):
    if type(count) is not int or count < 1:
        raise ValueError('seed schedule requires a positive iteration count')
    iteration_seed(base, count - 1)
    return list(range(base, base + count))
