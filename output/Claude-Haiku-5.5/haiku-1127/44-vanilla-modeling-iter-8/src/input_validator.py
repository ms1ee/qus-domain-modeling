"""Validation of user input for the command-line interface."""


class InputError(ValueError):
    """Raised when user input is invalid."""


FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_query(text):
    """Split a 'Starting Station; Ending Station' string.

    Returns:
        tuple: (raw start name, raw end name), both stripped.

    Raises:
        InputError: If the format is wrong.
    """
    if text.count(";") != 1:
        raise InputError(FORMAT_HINT)
    start, end = [part.strip() for part in text.split(";")]
    if not start or not end:
        raise InputError(FORMAT_HINT)
    return start, end


def validate_query(network, text):
    """Parse and validate a query against the network.

    Returns:
        tuple: (official start name, official end name).

    Raises:
        InputError: On format, existence or logic errors.
    """
    raw_start, raw_end = parse_query(text)
    start = network.standardize_name(raw_start)
    if start is None:
        raise InputError("Starting station '%s' does not exist, please check the station name" % raw_start)
    end = network.standardize_name(raw_end)
    if end is None:
        raise InputError("Ending station '%s' does not exist, please check the station name" % raw_end)
    if start == end:
        raise InputError("Starting station cannot be the same as the ending station")
    return start, end


def validate_line_preference(network, line):
    """Return the official line name matching ``line`` (case and space insensitive).

    Raises:
        InputError: If the line does not exist.
    """
    key = "".join(str(line).split()).casefold()
    for official in network.line_names():
        if "".join(official.split()).casefold() == key:
            return official
    raise InputError("Line '%s' does not exist. Available lines: %s"
                     % (line, ", ".join(network.line_names())))
