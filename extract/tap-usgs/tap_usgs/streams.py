"""Stream definitions for tap-usgs."""
from __future__ import annotations

from datetime import datetime, timezone

from singer_sdk import typing as th
from singer_sdk.streams import RESTStream


def _ms_to_iso(ms):
    """USGS sends epoch milliseconds; convert to an ISO8601 UTC string."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


class EarthquakesStream(RESTStream):
    """Earthquake events from the USGS FDSN event web service."""

    name = "earthquakes"
    url_base = "https://earthquake.usgs.gov/fdsnws/event/1"
    path = "/query"
    primary_keys = ["id"]
    replication_key = "time"   # <-- this turns on incremental loading
    is_sorted = True
    records_jsonpath = "$.features[*]"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("time", th.DateTimeType),
        th.Property("updated", th.DateTimeType),
        th.Property("mag", th.NumberType),
        th.Property("mag_type", th.StringType),
        th.Property("place", th.StringType),
        th.Property("longitude", th.NumberType),
        th.Property("latitude", th.NumberType),
        th.Property("depth_km", th.NumberType),
        th.Property("significance", th.IntegerType),
        th.Property("tsunami", th.IntegerType),
        th.Property("alert", th.StringType),
        th.Property("status", th.StringType),
        th.Property("felt", th.IntegerType),
        th.Property("event_type", th.StringType),
        th.Property("url", th.StringType),
    ).to_dict()

    @property
    def http_headers(self):
        headers = super().http_headers
        headers["User-Agent"] = "seismo-elt-student-project/0.1 (Meltano tap-usgs)"
        return headers

    def get_url_params(self, context, next_page_token):
        params = {
            "format": "geojson",
            "orderby": "time-asc",
            "minmagnitude": self.config.get("min_magnitude", 4.5),
            "limit": 20000,
        }
        starting = self.get_starting_timestamp(context)
        if starting:                                  # incremental: only newer events
            params["starttime"] = starting.isoformat()
        elif self.config.get("start_date"):
            params["starttime"] = self.config["start_date"]
        return params

    def post_process(self, row, context=None):
        """Flatten the nested GeoJSON feature into a clean, flat row."""
        props = row.get("properties") or {}
        coords = (row.get("geometry") or {}).get("coordinates") or [None, None, None]
        return {
            "id": row.get("id"),
            "time": _ms_to_iso(props.get("time")),
            "updated": _ms_to_iso(props.get("updated")),
            "mag": props.get("mag"),
            "mag_type": props.get("magType"),
            "place": props.get("place"),
            "longitude": coords[0] if len(coords) > 0 else None,
            "latitude": coords[1] if len(coords) > 1 else None,
            "depth_km": coords[2] if len(coords) > 2 else None,
            "significance": props.get("sig"),
            "tsunami": props.get("tsunami"),
            "alert": props.get("alert"),
            "status": props.get("status"),
            "felt": props.get("felt"),
            "event_type": props.get("type"),
            "url": props.get("url"),
        }