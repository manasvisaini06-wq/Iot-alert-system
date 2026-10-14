"""
alert_system.py
----------------
Polls Project 2's Sensor Data REST API for new readings and checks each
one against configured thresholds (temperature too high, humidity too
high, motion detected). When a threshold is crossed, it fires an alert.

This is the piece that was only a "hook" (a print statement) inside
Project 1's dashboard.py -- here it's built out properly as its own
standalone service, decoupled from both the device (Project 1) and the
storage API (Project 2). In a real system this might run as a
scheduled job, a separate microservice, or a cloud function -- the
point is it's independent of where the data came from, it just reacts
to it.

HOW TO USE:
1. Make sure Project 2's API is running:  uvicorn main:app --reload
   (from the sensor-rest-api folder)
2. Run this script in a separate terminal: python alert_system.py
3. Feed it data -- either by posting readings manually via
   http://127.0.0.1:8000/docs, or by pointing Project 1's publisher.py
   at this API instead of the dashboard (see README for details).

ALERT CHANNELS:
- Console (always on) -- prints a clearly marked [ALERT] line.
- Webhook (optional) -- if the WEBHOOK_URL environment variable is set
  (e.g. a Slack or Discord incoming webhook URL), alerts are also POSTed
  there as a JSON message. Left optional since it needs a real webhook
  URL to test, which not everyone will have set up.
"""

import os
import time

import requests

API_BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL_SECONDS = 3

# --- Thresholds ----------------------------------------------------------
# In a real product these would likely be configurable per-device or
# stored in a database, not hardcoded -- kept simple here on purpose.
TEMP_HIGH_THRESHOLD_C = 40.0
HUMIDITY_HIGH_THRESHOLD_PCT = 80.0

# Optional: set this environment variable to also send alerts to a
# Slack/Discord webhook. If unset, alerts only print to the console.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")


def check_thresholds(reading: dict) -> list[str]:
    """
    Returns a list of human-readable alert messages for whichever
    thresholds this single reading violates (can be more than one,
    or none).
    """
    alerts = []
    device = reading["device_id"]

    if reading["temperature_c"] > TEMP_HIGH_THRESHOLD_C:
        alerts.append(
            f"HIGH TEMPERATURE on {device}: {reading['temperature_c']}\u00b0C "
            f"(threshold: {TEMP_HIGH_THRESHOLD_C}\u00b0C)"
        )

    if reading["humidity_pct"] > HUMIDITY_HIGH_THRESHOLD_PCT:
        alerts.append(
            f"HIGH HUMIDITY on {device}: {reading['humidity_pct']}% "
            f"(threshold: {HUMIDITY_HIGH_THRESHOLD_PCT}%)"
        )

    if reading["motion_detected"]:
        alerts.append(f"MOTION DETECTED on {device} at {reading['timestamp']}")

    return alerts


def send_alert(message: str):
    """Sends one alert through every configured channel."""
    print(f"[ALERT] {message}")

    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"content": message}, timeout=5)
        except requests.exceptions.RequestException as e:
            print(f"  (could not reach webhook: {e})")


def main():
    print(f"Monitoring {API_BASE_URL}/readings every "
          f"{POLL_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")
    if not WEBHOOK_URL:
        print("(WEBHOOK_URL not set -- alerts will only print to console)\n")

    # Tracks the highest reading id we've already checked, so the same
    # reading never triggers a duplicate alert on the next poll.
    last_seen_id = 0

    try:
        while True:
            try:
                response = requests.get(
                    f"{API_BASE_URL}/readings",
                    params={"limit": 20},
                    timeout=5,
                )
                response.raise_for_status()
                readings = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Could not reach the API: {e}")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # The API returns newest-first; process oldest-unseen-first
            # so alerts print in the order things actually happened.
            new_readings = [r for r in readings if r["id"] > last_seen_id]
            new_readings.sort(key=lambda r: r["id"])

            for reading in new_readings:
                for message in check_thresholds(reading):
                    send_alert(message)
                last_seen_id = max(last_seen_id, reading["id"])

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping alert monitor.")


if __name__ == "__main__":
    main()
