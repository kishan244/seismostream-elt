"""Alert target: fires notifications for significant earthquakes."""
from __future__ import annotations

from singer_sdk import Target
from singer_sdk import typing as th

from target_alert.sinks import AlertSink


class TargetAlert(Target):
    name = "target-alert"
    default_sink_class = AlertSink

    config_jsonschema = th.PropertiesList(
        th.Property("min_alert_magnitude", th.NumberType, default=6.0,
                    description="Fire an alert at or above this magnitude."),
        th.Property("alerts_file", th.StringType, default="output/alerts.log",
                    description="File where alerts are appended."),
        th.Property("webhook_url", th.StringType,
                    description="Optional Slack/Discord/generic incoming webhook URL."),
    ).to_dict()


if __name__ == "__main__":
    TargetAlert.cli()
    