from utils.llm_client import call_llm

def run(rca_output, remediation_output):
    return call_llm(
        "You are a Safe Automation Agent. Return safe simulated actions only.",
        f"""
Generate safe simulated automation output.

Rules:
- Return plain text only.
- Do not use markdown code blocks.
- Do not generate destructive commands.
- Do not modify manifests, registry, packages, services, cache, or config files.
- Do not use placeholder paths.
- Do not claim actions were executed.
- Say actions are simulation only.
- Never generate Linux commands for Windows incidents.
- Never generate Windows commands for Linux incidents.

Windows CBS Rules:
- If RCA/remediation mentions CBS, WindowsUpdateAgent, SQM, HRESULT, CBS_E_MANIFEST_INVALID_ITEM, or CBS_E_INVALID_PACKAGE, treat it as Windows CBS incident.
- For Windows CBS incidents, only provide safe investigation and validation commands.
- Allowed Windows CBS commands:
  DISM /Online /Cleanup-Image /ScanHealth
  sfc /scannow
  findstr /i "error failed HRESULT" C:\\Windows\\Logs\\CBS\\CBS.log

RCA:
{rca_output}

Remediation:
{remediation_output}

Return exactly:

Safe Investigation Commands:
1. ...
2. ...

Safe Validation Commands:
1. ...
2. ...

Ticket Update Summary:
...

Safety Note:
No real infrastructure was modified. All actions are simulated.
"""
    )