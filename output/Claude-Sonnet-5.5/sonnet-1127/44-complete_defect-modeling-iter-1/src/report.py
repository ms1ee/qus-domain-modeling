"""Route reports (text / JSON)."""
import json


def format_distance(m):
    if m < 1000:
        return f"{m} m"
    return f"{m / 1000.0:.2f} km"


def build_summary(query, route):
    return {
        "query": query,
        "path": route["stations"],
        "distance_m": route["distance"],
        "distance_km": round(route["distance"] / 1000.0, 2),
        "fare": route["fare"],
        "estimated_time_min": round(route["time"], 1),
        "transfer_count": route["transfers"],
        "transfer_stations": [t[0] for t in route["transfer_details"]],
        "lines": route["lines"],
    }


def to_json(query, route):
    return json.dumps(build_summary(query, route), ensure_ascii=False, indent=2)


def to_text(query, route):
    out = [f"Route: {query['start']} -> {query['end']}",
           "Stations: " + " -> ".join(route["stations"])]
    out.append("Segments:")
    for line, a, b in route["segments"]:
        out.append(f"  {line}: {a} -> {b}")
    out.append(f"Total distance: {format_distance(route['distance'])}")
    out.append(f"Transfers: {route['transfers']}")
    for st, fl, tl in route["transfer_details"]:
        out.append(f"  Transfer at {st}: {fl} -> {tl}")
    out.append("Lines: " + ", ".join(route["lines"]))
    out.append(f"Estimated time: {route['time']:.0f} min")
    out.append(f"Fare: {route['fare']} yuan")
    return "\n".join(out)
