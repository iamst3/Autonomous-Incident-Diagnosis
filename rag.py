import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
KB_PATH = "knowledge_base/incidents.json"

embedder = SentenceTransformer(MODEL_NAME)

with open(KB_PATH, "r") as f:
    docs = json.load(f)

texts = [
    f"{d['title']} symptoms: {d['symptoms']} root cause: {d['root_cause']} fix: {d['fix']}"
    for d in docs
]

embeddings = embedder.encode(texts)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

def retrieve_context(query, top_k=2):
    q = embedder.encode([query])
    q = np.array(q).astype("float32")
    distances, ids = index.search(q, top_k)

    results = []
    for idx in ids[0]:
        d = docs[idx]
        results.append(
            f"""
Title: {d['title']}
Symptoms: {d['symptoms']}
Root Cause: {d['root_cause']}
Fix: {d['fix']}
Commands: {d.get('commands', 'N/A')}
"""
        )

    return "\n".join(results)
