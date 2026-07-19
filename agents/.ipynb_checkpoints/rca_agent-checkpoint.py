from utils.llm_client import call_llm

def run(logs, anomaly_output, rag_context):
    return call_llm(
        "You are a Senior SRE Root Cause Analysis Agent. Return ONLY valid JSON.",
        f"""
Analyze the incident.

Return ONLY valid JSON with this exact schema:

{{
  "root_cause": "short label only, max 4 words",
  "confidence": 85,
  "severity": "Low | Medium | High | Critical",
  "blast_radius": "affected service names only",
  "reasoning": "one short sentence"
}}

Rules:
- root_cause must be a short incident category, not a sentence.
- Good root_cause examples: "Network Packet Loss", "Memory Leak", "Database Pool Exhaustion", "Disk Full", "CrashLoopBackOff", "Certificate Expired".
- Do not classify "high memory usage" as "Memory Leak" unless logs mention heap growth, OOM, repeated restarts, or continuous memory increase.
- If logs mention NullPointerException, missing token, authentication failure, or validation error, prefer root_cause "Input Validation Failure" or "Null Pointer Exception".
- Root cause should be based on the strongest error-level signal, not only warning-level symptoms.
- Bad root_cause example: "High packet loss, service unavailability, and HTTP 504 errors suggest..."
- blast_radius must contain service names only.
- Do not write generic phrases like "network infrastructure" or "application layer" unless directly present in logs.
- confidence must be an integer between 60 and 100.

Severity Classification Rules:
- Critical: Use Critical if logs mention HTTP 502, HTTP 503, HTTP 504, service unavailable, payment-service unreachable, certificate expired causing request failures, database unavailable, disk full, CrashLoopBackOff, or production outage.
- High: Use High if logs mention CPU above 90%, memory pressure, high latency, retry storm, degraded performance, or elevated error rate without full outage.
- Medium: Use Medium if there is partial degradation with limited user impact.
- Low: Use Low for warning-only events without user impact.

You MUST strictly follow the severity classification rules above.
Do not return markdown.
Do not return text outside JSON.

Logs:
{logs}

Anomaly Output:
{anomaly_output}

Retrieved Context:
{rag_context}
"""
    )