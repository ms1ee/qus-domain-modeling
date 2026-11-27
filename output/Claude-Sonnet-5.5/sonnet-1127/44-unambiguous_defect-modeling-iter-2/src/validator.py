"""Input validation."""
import re

SEPARATORS = r"[;；,，]"


class ValidationError(Exception):
    pass


class InputValidator:
    def __init__(self, data_manager):
        self.dm = data_manager

    def parse(self, text):
        """Return (start, end) or raise ValidationError."""
        parts = [p.strip() for p in re.split(SEPARATORS, text or "")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError("Input format incorrect, please use 'Starting Station; Ending Station' format")
        start, end = parts
        if not self.dm.has_station(start):
            raise ValidationError(f"Starting station '{start}' does not exist, please check the station name")
        if not self.dm.has_station(end):
            raise ValidationError(f"Ending station '{end}' does not exist, please check the station name")
        if start == end:
            raise ValidationError("Starting station cannot be the same as the ending station")
        return start, end
