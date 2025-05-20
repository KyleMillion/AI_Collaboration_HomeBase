
# Aegis Orchestrator MVP — Phase 0 Setup

This repository is the **initial scaffold** for the Agent Orchestrator MVP described in the Aegis blueprint.

## Contents
* `requirements.txt` — baseline Python dependencies  
* `src/` — Python package for Aegis agent code  
* `infrastructure/` — container configs (Prometheus, Grafana, Prefect)  
* `flows/` — Prefect example flow registry  

## Next Steps
1. `python -m venv .venv && source .venv/bin/activate`  
2. `pip install -r requirements.txt`  
3. `docker compose -f infrastructure/docker-compose.yml up -d`  
4. Register Prefect deployment: `prefect deploy flows/hello_flow.py`  
5. Begin adding specialized agents under `src/agents/`.

---
Generated: 2025-05-20
