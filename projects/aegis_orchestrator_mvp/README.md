# Aegis Orchestrator MVP — Phase 0 Setup

[![CI](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml)

**This project is managed under the AI Collaboration Home Base framework.**
-   **Collaboration Guidelines:** See `../../docs/methodologies/OUR_COLLABORATION_CHARTER.md`
-   **Aegis Interaction Protocol (if applicable):** See `../../docs/methodologies/AEGIS_COLLABORATION_PROTOCOL.md`
-   **Project Development Checklist:** This project follows the "Roadmap for an AI Persona / AI-Driven Automated Process." Refer to the `CHECKLIST.md` (to be added to this directory) for detailed phase tracking.

This repository is the **initial scaffold** for the Agent Orchestrator MVP described in the Aegis blueprint.

## Contents
* `requirements.txt` — baseline Python dependencies  
* `src/` — Python package for Aegis agent code  
* `infrastructure/` — container configs (Prometheus, Grafana, Prefect)  
* `flows/` — Prefect example flow registry  

## Next Steps
1. `python -m venv .venv && source .venv/bin/activate`  
2. `pip install -r requirements.txt`  
3. `docker compose -f infrastructure/docker-compose.yml up -d`  
4. Register Prefect deployment: `prefect deploy flows/hello_flow.py`  
5. Begin adding specialized agents under `src/agents/`.

---
Generated: 2025-05-20

## Risk / Review Layer
* `src/risk.py` — naive regex‑based risk scorer.
* Orchestrator injects a `human_approval` Prefect task at the flow head.
  * If risk score ≥0.6, the flow raises an exception → Prefect UI shows failure for manual retry.
  * Adjust patterns/thresholds as policies mature.

## Environment Variables

| Var | Purpose |
|-----|---------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook for notifications |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server for EmailAPI |
| `SMTP_USER` / `SMTP_PASS` | Email credentials |
| `SQLITE_DB_PATH` | Path to SQLite DB for analytics demo |
| `OPENAI_API_KEY` | Enables LLM planning mode in Planner | 

## Secrets Management

This project uses a `.env` file at the root of the `projects/aegis_orchestrator_mvp/` directory to manage secrets and environment-specific configurations. This file is explicitly ignored by Git (see `.gitignore`) and should never be committed to the repository.

To set up your local environment:
1. Copy the `.env.example` file to a new file named `.env` in the same directory (`projects/aegis_orchestrator_mvp/`).
   ```bash
   cp .env.example .env
   ```
2. Edit the `.env` file and populate it with your actual secrets (e.g., API keys, webhook URLs, database credentials).

The application code (e.g., adapters, agents) uses the `python-dotenv` library to automatically load these variables from the `.env` file into the environment when the application starts.

**Future Enhancements (Vault Integration Plan):**
For more robust secrets management in production environments, integration with a dedicated secrets management tool like HashiCorp Vault is planned. The current `.env` approach is suitable for local development and initial MVP stages. The transition to Vault would involve:
1. Setting up a Vault instance.
2. Defining access policies and roles.
3. Modifying the application to fetch secrets from Vault at runtime, potentially using a Vault client library or agent.
4. This stub entry serves as a reminder for this future enhancement as the project matures towards production readiness. 