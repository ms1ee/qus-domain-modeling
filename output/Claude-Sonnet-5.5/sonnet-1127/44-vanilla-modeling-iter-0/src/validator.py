"""Input validation."""


class InputValidator:
    FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"

    def __init__(self, graph):
        self.graph = graph

    def validate(self, text):
        """Return (ok, start, end, error_message)."""
        text = (text or "").replace("；", ";")
        parts = text.split(";")
        if len(parts) != 2:
            return False, None, None, self.FORMAT_ERROR
        start, end = parts[0].strip(), parts[1].strip()
        if not start or not end:
            return False, None, None, self.FORMAT_ERROR
        if start not in self.graph.station_to_number:
            return False, None, None, "Starting station '%s' does not exist, please check the station name" % start
        if end not in self.graph.station_to_number:
            return False, None, None, "Ending station '%s' does not exist, please check the station name" % end
        if start == end:
            return False, None, None, "Starting station cannot be the same as the ending station"
        return True, start, end, ""
