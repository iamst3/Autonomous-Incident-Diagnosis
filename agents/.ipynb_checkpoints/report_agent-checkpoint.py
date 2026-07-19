from utils.llm_client import call_llm

def run(anomaly, rca, remediation, automation):
    return call_llm(
        "You are a Senior Incident Manager creating executive reports.",
        f"""
Create a concise executive incident report.

Rules:
- Use severity exactly as provided in RCA.
- Do not recalculate severity.
- Do not output HTML.
- Do not include <p>, </p>, <div>, </div>.
- Use RCA as source of truth.
- Keep report concise.

Anomaly:
{anomaly}

RCA:
{rca}

Remediation:
{remediation}

Automation:
{automation}

Return sections:
1. Incident Summary
2. Severity
3. Root Cause
4. Business Impact
5. Actions Taken
6. MTTR Improvement
7. Prevention Plan
"""
    )