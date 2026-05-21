# Factory Analytics Productivity Demo

A single-page Streamlit app that pulls live data from the Factory Analytics API and renders a three-panel productivity-gain narrative.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your FACTORY_API_KEY
```

## Run

```bash
streamlit run app.py
```

## Features

- **KPI Row**: Total PRs, commits, avg autonomy ratio, peak DAU
- **Panel 1 - Adoption Trajectory**: DAU stacked by client type
- **Panel 2 - Output Amplification**: Files edited + PRs created, top languages
- **Panel 3 - Human Attention Reclaimed**: Autonomy ratio, turns per session, delegation distribution
- **Killer Chart**: Combined DAU + autonomy + PR output view

## API Requirements

- Requires a Factory API key with Manager or Owner role
- Data available from 2026-01-14, with 24-hour lag (cannot query today's date)
