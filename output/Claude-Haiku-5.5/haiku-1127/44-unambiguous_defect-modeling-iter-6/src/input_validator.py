"""Input parsing and station-name validation for the CLI."""

import difflib
import re
from typing import Iterable, List, Set, Tuple

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"[;\uff1b,\uff0c]")  # ';', full-width ';', ',', full-width ','


class InputValidationError(Exception):
    """Raised when user input is malformed or refers to unknown stations."""


class InputValidator:
    """Validates and standardises user-entered station queries."""

    def __init__(self, station_names: Iterable[str], separator: str = ";") -> None:
        self.separator = separator
        self._names: List[str] = list(station_names)
        self._name_set: Set[str] = set(self._names)
        self._folded = {}
        for name in self._names:
            self._folded.setdefault(name.casefold(), name)

    @staticmethod
    def normalize(raw: str) -> str:
        """Remove all whitespace (including full-width spaces) from a name."""
        return "".join(raw.split())

    def parse(self, text: str) -> Tuple[str, str]:
        """Split 'Start; End' input into two raw station names.

        Raises:
            InputValidationError: if the format is not 'Start<sep>End'.
        """
        parts = SEPARATOR_PATTERN.split(text)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise InputValidationError(FORMAT_ERROR_MESSAGE)
        return parts[0], parts[1]

    def standardize(self, raw: str) -> str:
        """Map a raw name to its official spelling when possible."""
        name = self.normalize(raw)
        if name in self._name_set:
            return name
        folded = name.casefold()
        if folded in self._folded:
            return self._folded[folded]
        if name.endswith("\u7ad9"):  # trailing '站' (station) suffix
            base = name[:-1]
            if base in self._name_set:
                return base
            if base.casefold() in self._folded:
                return self._folded[base.casefold()]
        return name

    def resolve(self, raw: str, role: str) -> str:
        """Return the official station name or raise a descriptive error.

        Args:
            raw: the name as typed by the user.
            role: 'Starting' or 'Ending', used in the error message.
        """
        name = self.standardize(raw)
        if name in self._name_set:
            return name
        message = f"{role} station '{raw.strip()}' does not exist, please check the station name"
        suggestions = difflib.get_close_matches(name, self._names, n=3, cutoff=0.6)
        if suggestions:
            message += f" (did you mean: {', '.join(suggestions)}?)"
        raise InputValidationError(message)

    @staticmethod
    def validate_pair(start: str, end: str) -> None:
        """Ensure the start and end stations differ."""
        if start == end:
            raise InputValidationError("Starting station cannot be the same as the ending station")
