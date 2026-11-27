"""Input validation."""
import difflib
import re


class InputValidator:
    def __init__(self, station_names):
        self.station_names = list(station_names)
        self._set = set(self.station_names)

    def parse(self, text):
        """Return (start, end) or raise ValueError."""
        parts = [p.strip() for p in re.split(r"[;,；，]", text or "")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
        return parts[0], parts[1]

    def match(self, name):
        """Return exact or nearest station name, or None."""
        name = name.strip()
        if name in self._set:
            return name
        m = difflib.get_close_matches(name, self.station_names, n=1, cutoff=0.5)
        return m[0] if m else None

    def validate(self, text):
        """Return (start, end) matched station names, or raise ValueError."""
        s, e = self.parse(text)
        ms = self.match(s)
        if ms is None:
            raise ValueError("Starting station '%s' does not exist, please check the station name" % s)
        me = self.match(e)
        if me is None:
            raise ValueError("Ending station '%s' does not exist, please check the station name" % e)
        if ms == me:
            raise ValueError("Starting station cannot be the same as the ending station")
        return ms, me
