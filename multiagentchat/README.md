# MultiAgentChat — CAI Backend

CrewAI **Flow** orchestrating the full SAD nine-agent sequential crew for CAIInfo user queries.

## Setup

```bash
cd multiagentchat
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
cp .env.example .env     # set OPENAI_API_KEY
python scripts/build_kb.py
```

## Run

```bash
# Flow CLI
python -m multiagentchat.main

# API server
uvicorn multiagentchat.api.app:app --reload --port 8000
```

## Knowledge Base

Place CAI PDF manuals in:

- `knowledge/pdf_fac_data/` — Facilities portal
- `knowledge/pdf_ins_data/` — Insurers portal

Then run `python scripts/build_kb.py`.

## Spec

See `project-context/2.build/backend-funcional-spec.md`.
