"""Sink logic for target-alert."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from singer_sdk.sinks import RecordSink


class AlertSink(RecordSink):
    """Evaluates each earthquake and raises an alert if it's significant."""

    def _is_significant(self, record) -> bool:
        threshold = self.config.get("min_alert_magnitude", 6.0)
        mag = record.get("mag")
        if mag is not None and mag >= threshold:
            return True
        if (record.get("tsunami") or 0) == 1:
            return True
        return False

    def _format(self, record) -> str:
        flag = "  [TSUNAMI]" if (record.get("tsunami") or 0) == 1 else ""
        return f"ALERT  M{record.get('mag')}  {record.get('place')}  @ {record.get('time')}{flag}"

    def process_record(self, record, context) -> None:
        if not self._is_significant(record):
            return

        msg = self._format(record)

        # 1) console (shows up in the meltano run log)
        self.logger.info("ALERT FIRED: %s", msg)

        # 2) append to an alerts file
        alerts_file = self.config.get("alerts_file", "output/alerts.log")
        Path(os.path.dirname(alerts_file) or ".").mkdir(parents=True, exist_ok=True)
        with open(alerts_file, "a") as f:
            f.write(json.dumps({
                "alerted_at": datetime.now(timezone.utc).isoformat(),
                "id": record.get("id"),
                "magnitude": float(record["mag"]) if record.get("mag") is not None else None,
                "place": record.get("place"),
                "time": record.get("time"),
                "tsunami": record.get("tsunami"),
            }, default=str) + "\n")

        # 3) optional: send to a real webhook if one is configured
        webhook = self.config.get("webhook_url")
        if webhook:
            try:
                requests.post(webhook, json={"text": f"🚨 {msg}"}, timeout=5)
            except Exception as e:
                self.logger.warning("Webhook post failed: %s", e)