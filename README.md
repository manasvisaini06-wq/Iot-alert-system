# IoT Alert System

A threshold-based monitoring service that watches sensor readings and
fires alerts when something crosses a defined limit (temperature too
high, humidity too high, or motion detected). This is the piece that
ties Projects 1 and 2 together into one coherent story.

## How the three projects fit together

```
Project 1: publisher.py  --sends readings-->  Project 2: Sensor REST API (stores in SQLite)
                                                        |
                                                        | polls for new readings
                                                        v
                                              Project 3: alert_system.py
                                                        |
                                                        v
                                          console log  /  webhook (Slack/Discord)
```

Project 1 showed a device sending data and a simple live dashboard.
Project 2 showed the same data properly stored and queryable through a
real API. This project shows the piece both of those only hinted at
(a `print()` inside an `if motion_detected` block) built out as its
own real, standalone service -- polling the API, checking rules, and
alerting through multiple channels.

## How to run it

1. Make sure Project 2's API is running first:
   ```
   cd sensor-rest-api
   uvicorn main:app --reload
   ```
2. In a separate terminal, install and run this project:
   ```
   pip install -r requirements.txt
   python alert_system.py
   ```
3. Feed it data -- either post readings manually via
   `http://127.0.0.1:8000/docs`, or edit Project 1's `publisher.py` to
   POST to `http://127.0.0.1:8000/readings` instead of the dashboard's
   `/api/ingest` (the payload shape is nearly identical).
4. Watch the alert terminal -- readings that cross a threshold print
   an `[ALERT]` line; normal readings print nothing.

### Optional: send alerts to Slack/Discord too

Set the `WEBHOOK_URL` environment variable to a Slack or Discord
incoming webhook URL before running the script, and alerts will also
be POSTed there, e.g. (Mac/Linux):
```
export WEBHOOK_URL="https://discord.com/api/webhooks/..."
python alert_system.py
```
On Windows (cmd): `set WEBHOOK_URL=https://...` before running.
If unset, alerts simply print to the console only -- this keeps the
project runnable with zero external setup.

## Design notes / talking points for interviews

- **Why polling instead of a push-based approach?** Polling is the
  simplest way to decouple this service from the API -- it doesn't
  need the API to know it exists. A more advanced version could use
  webhooks (the API calls this service when new data arrives) or a
  message queue, which would reduce latency and load, at the cost of
  more moving parts.
- **Why track `last_seen_id` instead of just re-checking everything
  every time?** Without it, the same high-temperature reading would
  re-trigger an alert on every single poll (every 3 seconds), which
  would spam whoever receives the alert. Tracking the last processed
  id ensures each reading is only ever evaluated once.
- **Why is the webhook optional via an environment variable, instead
  of hardcoded?** Keeps secrets/URLs out of the code (you'd never want
  to commit a real webhook URL to a public GitHub repo), and lets the
  same script run with or without that integration configured.
- **Why check multiple thresholds per reading instead of stopping at
  the first match?** A single reading could violate more than one rule
  at once (e.g. high temp AND motion) -- `check_thresholds` returns a
  list so nothing gets silently missed.
- **Known limitations / next steps:** thresholds are hardcoded rather
  than configurable per device or stored in a database; there's no
  "alert cooldown" beyond deduplication by id (a device stuck reading
  41\u00b0C repeatedly would still fire once per new reading, not once
  per incident); no persistent log of past alerts.
