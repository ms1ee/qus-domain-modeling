"""Input validation."""
import re


class InputValidator:
    def __init__(self, network):
        self.network = network

    def parse(self, text):
        """Return (start, end, messages). Raises ValueError with a user message on failure."""
        parts = [p.strip() for p in re.split(r"[;；,，]", text or "") if p.strip()]
        if len(parts) != 2:
            raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
        start, end = parts
        notes = []
        ms = self.network.match_station(start)
        if ms is None:
            raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
        me = self.network.match_station(end)
        if me is None:
            raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
        if ms != start:
            notes.append("Starting station '%s' matched to '%s'" % (start, ms))
        if me != end:
            notes.append("Ending station '%s' matched to '%s'" % (end, me))
        if ms == me:
            raise ValueError("Starting station cannot be the same as the ending station")
        return ms, me, notes
