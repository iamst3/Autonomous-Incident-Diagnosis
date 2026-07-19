from utils.llm_client import call_llm

def run(logs):

    return call_llm(
        "You are an Anomaly Detection Agent for production systems.",
        f"""
Analyze these logs and detect anomalies.

Return:
1. Anomalies Detected
2. Affected Services
3. Evidence
4. Severity Signal

Logs:
{logs}
"""
    )