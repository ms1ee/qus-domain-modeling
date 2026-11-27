"""Shared validation of experiment conditions before any model work."""


def validate_feedback_level(level):
    if type(level) is not int or level not in (1, 2, 3):
        raise ValueError('feedback_level must be 1, 2, or 3')
    return level
