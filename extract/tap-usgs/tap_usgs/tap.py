"""USGS earthquake tap, built with the Meltano Singer SDK."""
from __future__ import annotations

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_usgs.streams import EarthquakesStream


class TapUSGS(Tap):
    name = "tap-usgs"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "start_date",
            th.DateTimeType,
            description="Earliest event time to pull (ISO8601). "
            "If omitted, USGS returns roughly the last 30 days.",
        ),
        th.Property(
            "min_magnitude",
            th.NumberType,
            default=4.5,
            description="Minimum earthquake magnitude to include.",
        ),
    ).to_dict()

    def discover_streams(self) -> list[Stream]:
        return [EarthquakesStream(self)]


if __name__ == "__main__":
    TapUSGS.cli()