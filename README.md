# Autonomous Incident Diagnosis

A Streamlit-based incident diagnosis application built for multi-agent reasoning, root-cause analysis, remediation planning, and execution simulation.

## Features

- Anomaly detection from incident logs
- Root cause analysis with JSON-based reasoning
- Runbook retrieval via RAG and FAISS
- Remediation, automation, and executive report generation
- Built for AMD Developer Cloud / vLLM workflows

## Repository Contents

- `app.py` — Streamlit user interface
- `rag.py` — semantic retrieval over `knowledge_base/incidents.json`
- `agents/` — modular agent prompts for anomaly, RCA, remediation, automation, and reporting
- `utils/llm_client.py` — vLLM client wrapper
- `start_app.sh` — convenience script for running Streamlit
- `requirements.txt` — Python dependencies
- `.github/workflows/python-app.yml` — CI workflow

## Local setup

### 1. Install dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 2. Run the app

```bash
python3 -m streamlit run app.py --server.address 0.0.0.0 --server.port 8502
```

Open `http://localhost:8502` in your browser.

### 3. Optional local LLM mock

For local testing without a live vLLM endpoint:

```bash
python3 mock_vllm.py
```

### 4. Configure AMD cloud vLLM

Set environment variables before starting the app:

```bash
export VLLM_URL="https://your-amd-vllm.example.com/v1/chat/completions"
export LLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
export VLLM_API_KEY="your_api_key"
```

## GitHub Actions CI

The repository includes a GitHub Actions workflow at `.github/workflows/python-app.yml` that:

- checks out the code
- installs Python 3.11
- installs `requirements.txt`
- runs `flake8` linting
- performs a compile-only import check

## Notes

- If you want to use a real vLLM, ensure `VLLM_URL` is reachable from the runtime environment.
- The app currently expects the `knowledge_base/incidents.json` file to exist for retrieval.
- `start_app.sh` is provided as a helper script if you prefer a shell wrapper.

## Recommended next steps

1. Add `mock_vllm.py` to the repo if you want local LLM testing.
2. Add a `requirements-dev.txt` for CI-only dependencies like `flake8`.
3. Enable GitHub Actions on the repository and verify the workflow file is detected.
