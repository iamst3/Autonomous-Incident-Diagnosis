import requests

MODEL = "Qwen/Qwen2.5-7B-Instruct"
VLLM_URL = "http://localhost:8000/v1/chat/completions"

def call_llm(system_prompt, user_prompt, max_tokens=700):

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }

    response = requests.post(
        VLLM_URL,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]
