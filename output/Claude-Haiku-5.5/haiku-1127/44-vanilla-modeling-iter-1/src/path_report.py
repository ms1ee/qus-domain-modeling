"""Path visualization, summary generation and report export."""

import json

from src.models import PathReport, PathSummary, Route

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)
SEPARATOR = "-" * 60


def format_distance(meters: float) -> str:
    """Meters for short distances, kilometers (with meters) for long distances."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(route: Route) -> PathSummary:
    """Extract key figures from a route."""
    return PathSummary(
        total_distance_km=route.total_distance / 1000.0,
        total_fare=route.fare.amount,
        transfer_count=route.transfer_count,
        estimated_time_minutes=route.estimated_time,
    )


def render_text(route: Route) -> str:
    """Console-formatted description of a route."""
    summary = build_summary(route)
    out: list[str] = []
    out.append("=" * 60)
    out.append("Beijing Subway Route Query")
    out.append("=" * 60)
    out.append(f"Query: {route.start} -> {route.end}")
    out.append(f"Mode: {route.mode}")
    out.append("")
    out.append(f"Station sequence ({len(route.stations)} stations):")
    for idx, name in enumerate(route.stations, 1):
        out.append(f"  {idx:>2}. {name}")
    out.append("")
    out.append("Line segments:")
    for idx, seg in enumerate(route.segments, 1):
        out.append(
            f"  {idx}. [{seg.line_name}] {seg.start_station} -> {seg.end_station} "
            f"({seg.station_count} stations, {format_distance(seg.distance)})"
        )
    out.append("")
    if route.transfers:
        out.append(f"Transfer stations ({len(route.transfers)}):")
        for t in route.transfers:
            out.append(f"  - {t.station_name}: {t.from_line} -> {t.to_line}")
    else:
        out.append("Transfer stations: none")
    out.append(f"Lines involved: {', '.join(route.lines)}")
    out.append("")
    out.append(f"Total distance: {format_distance(route.total_distance)}")
    out.append(f"Transfers: {route.transfer_count}")
    out.append(f"Estimated time: {summary.estimated_time_minutes:.1f} minutes")
    out.append(f"Fare: {route.fare.amount} yuan")
    return "\n".join(out)


def route_to_dict(route: Route) -> dict:
    """Structured representation of a route for programmatic use."""
    summary = build_summary(route)
    return {
        "query": {"start": route.start, "end": route.end, "mode": route.mode},
        "path": list(route.stations),
        "distance": {
            "meters": round(route.total_distance, 1),
            "kilometers": round(summary.total_distance_km, 3),
        },
        "fare": {"amount": route.fare.amount, "currency": route.fare.currency},
        "estimated_time_minutes": round(summary.estimated_time_minutes, 1),
        "transfer_count": route.transfer_count,
        "lines": list(route.lines),
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {
                "line": s.line_name,
                "start_station": s.start_station,
                "end_station": s.end_station,
                "distance_m": round(s.distance, 1),
                "station_count": s.station_count,
            }
            for s in route.segments
        ],
    }


def render_json(route: Route, indent: int = 2) -> str:
    """JSON representation of a route."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=indent)


def build_report(route: Route, fmt: str = FORMAT_TEXT) -> PathReport:
    """Render a route in the requested format."""
    if fmt == FORMAT_TEXT:
        content = render_text(route)
    elif fmt == FORMAT_JSON:
        content = render_json(route)
    else:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return PathReport(format=fmt, content=content, output_file=None)


def write_report(report: PathReport, path: str) -> PathReport:
    """Append a report to a file.

    Text reports are appended with a separator line. JSON reports are appended
    in compact JSON Lines form (one object per line), so repeated queries stay
    machine-readable.
    """
    if report.format == FORMAT_JSON:
        payload = json.dumps(json.loads(report.content), ensure_ascii=False)
        block = payload + "\n"
    else:
        block = report.content + "\n" + SEPARATOR + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(block)
    return PathReport(format=report.format, content=report.content, output_file=path)
