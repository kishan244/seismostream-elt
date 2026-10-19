# SeismoStream — live earthquake data pipeline

![CI](https://github.com/kishan244/seismostream-elt/actions/workflows/ci.yml/badge.svg)

A live ELT pipeline for earthquakes, built with **Meltano**. It pulls new earthquakes
from the USGS API every hour, stores them in **DuckDB**, models and tests them with
**dbt**, sends alerts for big events, and shows everything in a **Streamlit** dashboard.
The whole thing is code: versioned, tested in CI, and repeatable with one command.

## Results (last full run)

| | |
|---|---|
| Earthquakes loaded | 515 (magnitude 4.5+) |
| Strongest event | magnitude 7.8 |
| Spatial clusters found (DBSCAN) | 42 |
| Alerts fired (M 6.0+ or tsunami flag) | 19 |
| dbt data-quality tests | 6 / 6 passing |

Main finding: magnitude measures energy, exposure measures impact. A moderate quake next
to a big city can threaten more people than a huge one far offshore, and the exposure
score makes that visible.

## How it works

```
USGS API ──► tap-usgs ──► target-duckdb ──► DuckDB (raw)
                │                              │
                └──► target-alert ──► alerts.log / Slack / Discord webhook
                                               │
                                     dbt: staging ──► marts (+ snapshot)
                                               │
                      Python: exposure score + DBSCAN ──► Streamlit dashboard
```

1. **Extract** – `extract/tap-usgs` is a custom Singer tap (Meltano SDK). It loads
   incrementally: it remembers the last event it saw and only asks for newer ones.
2. **Load** – `target-duckdb` writes the raw records into `warehouse.duckdb`, untouched.
3. **Transform** – dbt builds `raw → staging → marts`. Staging adds fields like
   magnitude class and seismic energy in joules.
4. **Test** – 6 dbt tests (unique, not null, accepted values and a custom test that
   rejects impossible values) run on every pipeline run.
5. **History** – a dbt snapshot (SCD Type 2) keeps every revision of a quake, so when
   USGS corrects a magnitude the old value is kept with its valid-from/valid-to time.
6. **Alert** – `load/target-alert` is a second custom Singer target. It fires an alert
   for magnitude 6.0+ or a tsunami flag, to a log file or a Slack/Discord webhook.
7. **Analyse** – `analyze/seismic_analytics.py` scores population exposure (magnitude,
   city population, distance) and groups quakes into active zones with DBSCAN.
8. **Show** – `analyze/dashboard.py` is a Streamlit app: world map, activity charts,
   exposure leaderboard.
9. **Automate** – everything runs as one Meltano job on an hourly schedule, and GitHub
   Actions runs extract → load → transform → tests on every push.

## Tech stack

Meltano · Singer SDK · DuckDB · dbt (dbt-duckdb) · Python · pandas · scikit-learn ·
Streamlit · Plotly · GitHub Actions

## Run it

```bash
pipx install meltano
meltano install                       # installs the taps, targets and dbt

meltano run seismo_pipeline           # full job: extract, load, dbt run + snapshot, alerts
meltano invoke dbt-duckdb:test        # data-quality tests

pip install -r requirements.txt
python analyze/seismic_analytics.py   # exposure score + clusters
streamlit run analyze/dashboard.py    # dashboard
```

Optional: set a webhook for alerts with
`meltano config target-alert set webhook_url <your-url>` (stored in `.env`, never committed).

## Project layout

| Folder | What is inside |
|---|---|
| `extract/tap-usgs/` | custom Singer tap for the USGS API |
| `load/target-alert/` | custom Singer target that sends alerts |
| `transform/` | dbt project: models, tests, snapshot |
| `analyze/` | exposure scoring, DBSCAN, Streamlit dashboard |
| `.github/workflows/ci.yml` | CI: runs the pipeline and the tests |
| `meltano.yml` | plugins, job and hourly schedule |

## Data

Earthquake data from the [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/fdsnws/event/1/)
(public domain).
