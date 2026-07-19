from utils.llm_client import call_llm

def run(logs, rca_output):
    return call_llm(
        "You are a Production Remediation Agent. Return ONLY 5 numbered actionable steps.",
        f"""
Generate specific remediation actions for this incident.

Rules:
- Return exactly 5 numbered actions.
- Each action must be operational and specific.
- Do not return headings.
- Do not return markdown.
- Do not return generic actions like "Review incident details".
- Actions must match the root cause.
- Use only services/components present in logs or RCA.
- Do not invent service names.

Critical Safety Rules:
- Detect operating system from logs before generating actions.
- Never generate Linux commands for Windows incidents.
- Never generate Windows commands for Linux incidents.
- Never modify manifest, registry, system packages, or configuration files directly.
- Do not use placeholder paths such as /path/to/*, /tmp/*, or C:\\temp\\example.
- If RCA confidence is less than 90, provide investigation and validation steps instead of risky remediation commands.
- Every action must be traceable to log evidence or retrieved knowledge.

Windows CBS Log Rules:
- If logs mention CBS, WindowsUpdateAgent, HRESULT, CBS_E_MANIFEST_INVALID_ITEM, or CBS_E_INVALID_PACKAGE, treat it as a Windows incident.
- For Windows CBS incidents, prefer safe investigation/validation actions such as DISM health scan, SFC scan, Windows Update log review, and checking failed package IDs.
- Do not suggest apt-get, kubectl, sed, grep on Linux paths, or editing Windows manifests directly.

Logs:
{logs}

RCA:
{rca_output}

Example for Network Packet Loss:
1. Check packet loss between gateway and payment-service
2. Verify service mesh and ingress gateway health
3. Restart unhealthy payment-service pods
4. Reroute traffic away from degraded node or zone
5. Monitor HTTP 504 rate and packet loss after mitigation
"""
    )