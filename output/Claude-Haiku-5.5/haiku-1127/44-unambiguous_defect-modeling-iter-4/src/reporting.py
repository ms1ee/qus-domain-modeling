"""Path visualisation and report export (console text, JSON and files)."""
import json

from errors import ReportExportError


def build_path_summary(route):
    """Extract key figures of a route into a plain dictionary."""
    return {
        "total_distance_km": round(route.distance_km, 2),
        "total_fare_yuan": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time_min,
    }


def build_json_report(route):
    """Build the structured data representation of a route."""
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.preferred_lines or None,
        },
        "path": {
            "stations": list(route.station_names),
            "station_count": len(route.station_names),
            "segments": [
                {"line": seg.line, "stations": list(seg.stations)}
                for seg in route.segments
            ],
        },
        "distance_m": round(route.distance_m, 1),
        "distance_km": round(route.distance_km, 3),
        "fare": route.fare,
        "estimated_time_minutes": route.estimated_time_min,
        "transfer_count": route.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": list(route.lines),
        "summary": build_path_summary(route),
    }


def format_json(route):
    """Render a route as an indented JSON document."""
    return json.dumps(build_json_report(route), ensure_ascii=False, indent=2)


def format_text(route):
    """Render a route as a human-readable console report."""
    rule = "=" * 68
    thin = "-" * 68
    max_text = "unlimited" if route.max_transfers is None else str(route.max_transfers)
    pref_text = ", ".join(route.preferred_lines) if route.preferred_lines else "none"

    out = [
        rule,
        "Beijing Subway Fare Report",
        rule,
        "Query          : {} -> {}".format(route.start, route.end),
        "Mode           : {}".format(route.mode),
        "Max transfers  : {}".format(max_text),
        "Line preference: {}".format(pref_text),
        thin,
        "Station sequence ({} stations):".format(len(route.station_names)),
    ]
    for index, name in enumerate(route.station_names, 1):
        out.append("  {:>3}. {}".format(index, name))

    out.append(thin)
    out.append("Line segments:")
    for index, segment in enumerate(route.segments, 1):
        stops = len(segment.stations) - 1
        out.append(
            "  {}. [{}] {}  ({} stop{})".format(
                index,
                segment.line,
                " -> ".join(segment.stations),
                stops,
                "" if stops == 1 else "s",
            )
        )

    out.append(thin)
    if route.transfers:
        out.append("Transfers ({}):".format(len(route.transfers)))
        for index, transfer in enumerate(route.transfers, 1):
            out.append(
                "  {}. at {}: {} -> {}".format(
                    index, transfer.station, transfer.from_line, transfer.to_line
                )
            )
    else:
        out.append("Transfers: none")
    out.append("Lines involved: {}".format(", ".join(route.lines)))
    out.append(thin)
    out.append(
        "Total distance: {:,.0f} m ({:.2f} km)".format(route.distance_m, route.distance_km)
    )
    out.append("Transfer count: {}".format(route.transfer_count))
    out.append("Estimated time: {:.1f} min".format(route.estimated_time_min))
    out.append("Fare: {} yuan".format(route.fare))
    out.append(rule)
    return "\n".join(out)


def render_report(route, fmt):
    """Render a route in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(route)
    if fmt == "text":
        return format_text(route)
    raise ValueError("unsupported report format '{}'".format(fmt))


def write_report_file(path, content):
    """Write report content to a UTF-8 text file.

    Raises:
        ReportExportError: if the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
    except OSError as exc:
        raise ReportExportError("cannot write output file '{}': {}".format(path, exc)) from exc
