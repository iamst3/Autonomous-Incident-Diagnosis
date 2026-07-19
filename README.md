# AGENTS_026_Project

A Streamlit-based incident diagnosis application using multi-agent reasoning and RAG.

## Run locally

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Start the project:

```bash
python3 -m streamlit run app.py --server.address 0.0.0.0 --server.port 8502
```

3. Optional: run a mock vLLM server for local testing:

```bash
python3 mock_vllm.py
```

4. Configure a real VLLM endpoint via environment variables:

```bash
export VLLM_URL="https://your-amd-vllm.example.com/v1/chat/completions"
export LLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
export VLLM_API_KEY="your_api_key"
```

## Notes

- The app uses `utils/llm_client.py` for LLM calls.
- `rag.py` builds a FAISS vector index from `knowledge_base/incidents.json`.
- `start_app.sh` launches the Streamlit app with server settings.
