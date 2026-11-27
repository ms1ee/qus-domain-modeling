"""Path visualization, summary generation and report export."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def build_path_report(network, route, query):
    """Build a structured report describing a computed route.

    Args:
        network: SubwayNetwork used to translate station numbers to names.
        route: pathfinding.Route for the query.
        query: dict with keys start, end, mode, max_transfers, line_preference.

    Returns:
        dict with the query information, station sequence, line segments,
        transfer details, distance (meters and kilometers), fare, estimated
        time, transfer count and involved lines.
    """
    stations = [network.name_of(number) for number in route.stations]

    segments = []
    transfers = []
    for index, edge in enumerate(route.edges):
        from_name = stations[index]
        to_name = stations[index + 1]
        if segments and segments[-1]["line"] == edge.line:
            segment = segments[-1]
            segment["to"] = to_name
            segment["stations"].append(to_name)
            segment["distance_m"] += edge.distance
        else:
            if segments:
                transfers.append(
                    {
                        "station": from_name,
                        "from_line": segments[-1]["line"],
                        "to_line": edge.line,
                        "lines_at_station": network.lines_of(from_name),
                    }
                )
            segments.append(
                {
                    "line": edge.line,
                    "from": from_name,
                    "to": to_name,
                    "stations": [from_name, to_name],
                    "distance_m": edge.distance,
                }
            )

    total_meters = route.distance
    fare = Sum_money(total_meters)
    estimated_minutes = calculate_estimated_time(total_meters, route.transfer_count)

    lines_involved = []
    for segment in segments:
        if segment["line"] not in lines_involved:
            lines_involved.append(segment["line"])

    return {
        "query": {
            "start": query["start"],
            "end": query["end"],
            "mode": query["mode"],
            "max_transfers": query.get("max_transfers"),
            "line_preference": list(query.get("line_preference") or []),
        },
        "path": stations,
        "segments": segments,
        "transfers": transfers,
        "distance": {
            "meters": total_meters,
            "kilometers": round(total_meters / 1000.0, 3),
        },
        "fare": fare,
        "estimated_time_minutes": estimated_minutes,
        "transfer_count": route.transfer_count,
        "lines": lines_involved,
    }


def format_text_report(report):
    """Render a path report as console-friendly text."""
    query = report["query"]
    path = report["path"]
    distance = report["distance"]
    max_transfers = query["max_transfers"]
    preference = ", ".join(query["line_preference"]) or "none"

    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append(f"From: {query['start']}    To: {query['end']}")
    out.append(
        f"Mode: {query['mode']}    Max transfers: "
        f"{'unlimited' if max_transfers is None else max_transfers}"
    )
    out.append(f"Line preference: {preference}")
    out.append("-" * 60)

    out.append(f"Station sequence ({len(path)} stations):")
    for number, name in enumerate(path, start=1):
        out.append(f"  {number:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for segment in report["segments"]:
        stops = len(segment["stations"]) - 1
        out.append(
            f"  [{segment['line']}] {segment['from']} -> {segment['to']} "
            f"({stops} stops, {segment['distance_m']} m)"
        )
    out.append("")

    if report["transfers"]:
        out.append(f"Transfers ({len(report['transfers'])}):")
        for transfer in report["transfers"]:
            out.append(
                f"  - {transfer['station']}: {transfer['from_line']} -> "
                f"{transfer['to_line']} (lines at station: "
                f"{', '.join(transfer['lines_at_station'])})"
            )
    else:
        out.append("Transfers: none")
    out.append("")

    out.append(
        f"Total distance: {distance['meters']} m ({distance['kilometers']:.2f} km)"
    )
    out.append(f"Transfer count: {report['transfer_count']}")
    out.append(f"Lines involved: {', '.join(report['lines'])}")
    out.append(f"Estimated travel time: {report['estimated_time_minutes']} minutes")
    out.append(f"Fare: {report['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json_report(report):
    """Render a path report as an indented JSON document."""
    return json.dumps(report, ensure_ascii=False, indent=2)
