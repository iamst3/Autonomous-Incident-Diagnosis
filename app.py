import streamlit as st
import requests
import re
from rag import retrieve_context
from agents.anomaly_agent import run as anomaly_agent
from agents.rca_agent import run as rca_agent
from agents.remediation_agent import run as remediation_agent
from agents.automation_agent import run as automation_agent
from agents.report_agent import run as report_agent
from utils.llm_client import call_llm
import json

MODEL = "Qwen/Qwen2.5-7B-Instruct"
VLLM_URL = "http://localhost:8000/v1/chat/completions"

st.set_page_config(page_title="AGENTS_026", layout="wide")

st.markdown("""
<style>
header[data-testid="stHeader"] {
    background: #050b18;
    height: 0px;
}
.stApp {
    background: #050b18;
    color: white;
}
.block-container {
    padding-top: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
section[data-testid="stSidebar"] {
    background: #0b1220;
}
h1, h2, h3, h4, p, label, span, div {
    color: #f8fafc;
}
textarea {
    background-color: #0f172a !important;
    color: white !important;
    border: 1px solid #334155 !important;
}
div.stButton > button {
    color: white !important;
    border-radius: 12px !important;
    border: 1px solid #334155 !important;
    background: #111827 !important;
}

div.stButton > button:hover {
    border-color: #8b5cf6 !important;
    background: #1e1b4b !important;
}
.card {
    background:#111827;
    border:1px solid #24324a;
    border-radius:18px;
    padding:24px;
    min-height:220px;
}
.root-card {
    background:#2a0d15;
    border:1px solid #ff4d4f;
    padding:20px;
    border-radius:16px;
}
.action-card {
    background:#182235;
    padding:16px;
    border-radius:12px;
    margin-bottom:12px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.action-badge {
    background:#1f6feb;
    color:white;
    padding:6px 12px;
    border-radius:8px;
}
.confidence-circle {
    width:120px;
    height:120px;
    border-radius:50%;
    border:8px solid #00ff88;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:34px;
    font-weight:bold;
    color:#00ff88;
}
.amd-badge {
    display:inline-block;
    border:1px solid #f97316;
    color:#f97316 !important;
    padding:12px 20px;
    border-radius:12px;
    text-align:center;
    font-weight:700;
    white-space:nowrap;
    margin-top:12px;
    float:right;
}
.ai-box {
    background:#0f172a;
    padding:20px;
    border-radius:14px;
    border:1px solid #24324a;
}
section[data-testid="stSidebar"] label {
    font-size: 18px !important;
    font-weight: 600 !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 12px !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
    background: #111827;
}
</style>
""", unsafe_allow_html=True)

def extract_confidence(text):
    match = re.search(r"(\d{2,3})\s*%", text)
    if match:
        return min(int(match.group(1)), 100)
    return 94
def extract_root_cause(rca_text):
    lines = rca_text.split("\n")
    for line in lines:
        if "root cause" in line.lower() and len(line.strip()) > 5:
            return line.replace("*", "").replace("#", "").strip()
    for line in lines:
        if line.strip():
            return line.replace("*", "").replace("#", "").strip()
    return "Root cause unavailable"

def parse_json_from_llm(text):
    text = text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return json.loads(text)


def extract_actions(remediation_text):
    actions = []

    for line in remediation_text.split("\n"):
        clean = line.strip().replace("*", "").replace("-", "").strip()

        if re.match(r"^\d+\.\s+", clean):
            clean = re.sub(r"^\d+\.\s+", "", clean).strip()

            if len(clean) > 5:
                actions.append(clean)

    return actions[:5] if actions else [
        "Check affected service health",
        "Restart unhealthy service pods",
        "Validate gateway and dependency connectivity",
        "Monitor error rate and latency",
        "Confirm recovery after mitigation"
    ]

def filter_log_lines(logs, max_lines=80):
    keywords = [
        "error", "failed", "warning", "critical", "exception",
        "timeout", "unavailable", "denied", "invalid", "crash",
        "0x800", "HRESULT"
    ]

    selected = []
    for line in logs.splitlines():
        if any(k in line.lower() for k in keywords):
            selected.append(line)

    return "\n".join(selected[:max_lines]) if selected else "\n".join(logs.splitlines()[:max_lines])

def shorten_root_cause(text):
    text = str(text).strip()
    lowered = text.lower()

    if "cbs" in lowered or "manifest" in lowered or "0x800f080d" in lowered:
        return "CBS Manifest Invalid"

    if "invalid package" in lowered or "0x800f0805" in lowered:
        return "Invalid Package"

    if len(text.split()) <= 6:
        return text

    if "packet loss" in lowered or "504" in lowered or "unreachable" in lowered:
        return "Network Packet Loss"

    if "memory" in lowered or "oom" in lowered or "heap" in lowered:
        return "Memory Leak"

    if "connection pool" in lowered or "database" in lowered or "postgres" in lowered:
        return "Database Pool Exhaustion"

    if "disk" in lowered or "wal" in lowered:
        return "Disk Full"

    if "crashloop" in lowered or "crash" in lowered:
        return "CrashLoopBackOff"

    return "Service Degradation"

with st.sidebar:
    st.markdown("""
    <h1 style='color:white;'>🤖 AGENTS_026</h1>
    <p style='color:#94a3b8;'>Autonomous Incident Diagnosis</p>
    <hr>
    """, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    if st.button("🏠 Dashboard", key="nav_dashboard", use_container_width=True):
        st.session_state.page = "Dashboard"

    if st.button("🚨 Incidents", key="nav_incidents", use_container_width=True):
        st.session_state.page = "Incidents"

    if st.button("📘 Runbooks", key="nav_runbooks", use_container_width=True):
        st.session_state.page = "Runbooks"

    if st.button("🧠 Knowledge Base", key="nav_kb", use_container_width=True):
        st.session_state.page = "Knowledge Base"

    if st.button("📊 Metrics", key="nav_metrics", use_container_width=True):
        st.session_state.page = "Metrics"

    if st.button("⚙️ Settings", key="nav_settings", use_container_width=True):
        st.session_state.page = "Settings"

page = st.session_state.page

if page == "Incidents":
    st.title("🚨 Incidents")

    if "results" in st.session_state and st.session_state.results:

        root_cause = st.session_state.results.get(
            "root_cause",
            "No diagnosis available"
        )

        severity = st.session_state.results.get(
            "severity",
            "Unknown"
        )

        st.info(f"Active incident: {root_cause}")

        st.metric("Open Incidents", "1")
        st.metric("Severity", severity)

    else:
        st.warning("No incident diagnosis available yet. Run AI Agent Diagnosis first.")

    st.stop()

elif page == "Runbooks":
    st.title("📘 Incident Runbooks")

    if "retrieved_context" in st.session_state:
        st.markdown("### 🔎 Retrieved Similar Incident / Runbook")
        st.info(st.session_state.get("retrieved_context", "No runbook retrieved"))

        if "results" in st.session_state and st.session_state.results:
            st.markdown("### 🛠 Recommended Runbook Actions")
            st.write(st.session_state.results.get("remediation", "No remediation available"))

            st.markdown("### 🤖 Safe Automation Plan")
            st.write(st.session_state.results.get("automation", "No automation plan available"))
    else:
        st.warning("No runbook retrieved yet. Run AI Agent Diagnosis first.")

    st.stop()


elif page == "Knowledge Base":
    st.title("🧠 Knowledge Base")

    if "retrieved_context" in st.session_state:
        st.markdown("### Active Knowledge Context")
        st.write(st.session_state.get("retrieved_context", "No context available"))
    else:
        st.warning("No knowledge context available yet. Run AI Agent Diagnosis first.")

    st.stop()

elif page == "Metrics":
    st.title("📊 Incident Metrics")

    if "results" in st.session_state and st.session_state.results:

        confidence = st.session_state.results.get("confidence", 0)
        severity = st.session_state.results.get("severity", "Unknown")
        blast_radius = st.session_state.results.get("blast_radius", "Unknown")

        c1, c2, c3 = st.columns(3)
        c1.metric("Confidence", f"{confidence}%")
        c2.metric("Severity", severity)
        c3.metric("Blast Radius", blast_radius[:25])

        st.markdown("---")

        import pandas as pd

        # Confidence gauge-like chart
        st.subheader("Confidence Score")
        st.progress(confidence / 100)
        st.success(f"{confidence}% confidence based on AI agent evidence")

        st.subheader("Severity Level")

        severity_map = {
            "Critical": 100,
            "High": 75,
            "Medium": 50,
            "Low": 25
            }

        severity_score = severity_map.get(severity, 0)

        st.progress(severity_score / 100)

        st.info(f"Current incident severity: {severity}")

        st.subheader("Current Incident Summary")

        st.markdown(f"""
            - **Root Cause:** {st.session_state.results.get('root_cause', 'Unknown')}
            - **Severity:** {severity}
            - **Confidence:** {confidence}%
            - **Blast Radius:** {blast_radius}
            """)
        st.subheader("Diagnosis History")

        if "history" in st.session_state and len(st.session_state.history) > 0:
            import pandas as pd

            history_df = pd.DataFrame(st.session_state.history)

            st.dataframe(history_df)

            st.bar_chart(
            history_df["confidence"]
            )

    else:
        st.warning("No metrics available yet. Run AI Agent Diagnosis first.")

    st.stop()


elif page == "Settings":
    st.title("⚙️ Settings")

    st.markdown("""
    ### Runtime Configuration
    - Model: Qwen2.5-7B-Instruct
    - Inference Server: vLLM
    - Hardware Runtime: AMD ROCm
    - Architecture: Multi-Agent + RAG
    """)

    st.stop()

top_left, top_right = st.columns([4, 1])
with top_left:
    st.markdown("# Incident Diagnosis Dashboard")
    st.caption("AI Agents working together to resolve incidents")
with top_right:
    st.markdown("<div class='amd-badge'>AMD Developer Cloud</div>", unsafe_allow_html=True)

DEFAULT_LOGS = """2026-06-12 10:01 checkout-api CPU usage 95%
2026-06-12 10:02 database timeout errors increasing
2026-06-12 10:03 API latency 15 seconds
2026-06-12 10:04 checkout API returning HTTP 503
2026-06-12 10:05 postgres connection pool exhausted
2026-06-12 10:06 payment-service retry storm detected"""

if "saved_logs" not in st.session_state:
    st.session_state["saved_logs"] = DEFAULT_LOGS

if "logs_widget" not in st.session_state:
    st.session_state["logs_widget"] = st.session_state["saved_logs"]

def save_logs():
    st.session_state["saved_logs"] = st.session_state["logs_widget"]

uploaded_file = st.file_uploader(
    "Upload Incident Logs",
    type=["txt", "log", "csv", "json"]
)
demo_logs = {
    "Database Pool Exhaustion": """2026-06-12 10:01 checkout-api CPU usage 95%
2026-06-12 10:02 database timeout errors increasing
2026-06-12 10:03 API latency 15 seconds
2026-06-12 10:04 checkout API returning HTTP 503
2026-06-12 10:05 postgres connection pool exhausted""",

    "Memory Leak": """2026-06-14 11:10 recommendation-service memory usage 97%
2026-06-14 11:11 heap allocation continuously growing
2026-06-14 11:12 OOM warning detected
2026-06-14 11:13 pod restarted by Kubernetes
2026-06-14 11:15 service unavailable"""
}

selected_demo = st.selectbox(
    "🎯 Load Demo Incident",
    ["Select Demo"] + list(demo_logs.keys())
)

if selected_demo != "Select Demo":
    st.session_state["saved_logs"] = demo_logs[selected_demo]
    st.session_state["logs_widget"] = demo_logs[selected_demo]

if uploaded_file is not None:
    uploaded_logs = uploaded_file.read().decode("utf-8", errors="ignore")
    st.session_state["saved_logs"] = uploaded_logs
    st.session_state["logs_widget"] = uploaded_logs

    st.success(f"Loaded {len(uploaded_logs.splitlines())} log lines from file")

st.text_area(
    "Incident Logs",
    height=170,
    key="logs_widget",
    on_change=save_logs
)

raw_logs = st.session_state["logs_widget"]

logs = filter_log_lines(raw_logs)

st.session_state["saved_logs"] = raw_logs

st.caption(
    f"Analyzing {len(logs.splitlines())} important log lines "
    f"(from {len(raw_logs.splitlines())} total lines)"
)

if "results" not in st.session_state:
    st.session_state.results = {}

if st.button("Run AI Agent Diagnosis", type="primary"):
    try:
        progress = st.progress(0)
        status = st.empty()

        status.info("🔍 Running Anomaly Detection Agent...")
        retrieved_context = retrieve_context(logs)
        st.session_state["retrieved_context"] = retrieved_context
        anomaly = anomaly_agent(logs)
        progress.progress(20)

        status.info("🧠 Running Root Cause Agent...")
        rca = rca_agent(logs, anomaly, retrieved_context)

        try:
            rca_json = parse_json_from_llm(rca)

            root_cause = rca_json.get("root_cause", "Unknown Root Cause")
            root_cause = shorten_root_cause(root_cause)
            try:
                confidence = int(rca_json.get("confidence", 80))
            except Exception:
                confidence = 80

            if confidence <= 0:
                confidence = 80
            severity = rca_json.get("severity", "Unknown")
            blast_radius = rca_json.get("blast_radius", "Unknown")
            reasoning = rca_json.get("reasoning", root_cause)

        except Exception:
            root_cause = "Unable to parse RCA"
            confidence = 80
            severity = "Unknown"
            blast_radius = "Unknown"
            reasoning = rca
        
        progress.progress(45)

        status.info("🛠 Running Remediation Agent...")
        remediation = remediation_agent(logs, rca)
        progress.progress(65)

        status.info("🤖 Running Automation Agent...")
        automation = automation_agent(rca, remediation)
        progress.progress(85)

        status.info("📄 Generating Executive Report...")
        report = report_agent(anomaly, rca, remediation, automation)
        progress.progress(100)

        st.session_state.results = {
            "anomaly": anomaly,
            "rca": rca,
            "remediation": remediation,
            "automation": automation,
            "report": report,
            "root_cause": root_cause,
            "confidence": confidence,
            "severity": severity,
            "blast_radius": blast_radius,
            "reasoning": reasoning
        }
        if "history" not in st.session_state:
            st.session_state.history = []

        st.session_state.history.append({
            "confidence": confidence,
            "severity": severity,
            "root_cause": root_cause
        })

        status.success("✅ Multi-agent diagnosis completed")

    except Exception as e:
        st.error(f"Error: {e}")
        st.warning("Check whether vLLM is running on http://localhost:8000")

st.markdown("""
<style>

.hero-card{
    background:linear-gradient(135deg,#0f172a,#111827);
    border:1px solid #334155;
    border-radius:24px;
    padding:24px;
    margin-bottom:20px;
}

.glow-card{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:20px;
    padding:20px;
    transition:0.3s;
    margin-bottom:10px;
}

.glow-card:hover{
    border-color:#8b5cf6;
    box-shadow:0 0 20px rgba(139,92,246,.3);
}

.agent-card{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:18px;
    padding:18px;
    text-align:center;
    min-height:120px;
}

.agent-status{
    color:#22c55e;
    font-weight:bold;
}

.severity-pill{
    background:#7c3aed;
    padding:8px 16px;
    border-radius:999px;
    display:inline-block;
    font-size:14px;
}

.metric-number{
    font-size:36px;
    font-weight:700;
    color:#a855f7;
}

.timeline-card{
    background:#111827;
    border-left:4px solid #8b5cf6;
    padding:16px;
    border-radius:12px;
    margin-bottom:10px;
}

</style>
""", unsafe_allow_html=True)

if st.session_state.results:
    anomaly = st.session_state.results["anomaly"]
    rca = st.session_state.results["rca"]
    remediation = st.session_state.results["remediation"]
    automation = st.session_state.results["automation"]
    report = st.session_state.results["report"]

    confidence = st.session_state.results["confidence"]
    root_cause = st.session_state.results["root_cause"]
    severity = st.session_state.results["severity"]
    blast_radius = st.session_state.results["blast_radius"]
    reasoning = st.session_state.results["reasoning"]
    actions = extract_actions(remediation)

    st.markdown("---")

    st.markdown(f"""
    <div class="hero-card">
        <h1>🚨 Active Incident</h1>
        <div class="severity-pill">{severity}</div>
        <h2 style="margin-top:15px;">{root_cause}</h2>
        <p>Autonomous Incident Diagnosis powered by Multi-Agent AI + RAG + vLLM</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="glow-card">
            <h4>Confidence</h4>
            <div class="metric-number">{confidence}%</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="glow-card">
            <h4>Severity</h4>
            <div class="metric-number">{severity}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="glow-card">
            <h4>Blast Radius</h4>
            <div>{blast_radius}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## 🤖 AI Agent Workflow")

    a1, a2, a3, a4, a5 = st.columns(5)

    workflow_cards = [
        "Incident Analyzer",
        "Log Analyzer",
        "Knowledge Agent",
        "RCA Agent",
        "Resolution Agent"
    ]

    for col, title in zip([a1, a2, a3, a4, a5], workflow_cards):
        with col:
            st.markdown(f"""
            <div class="agent-card">
                <h4>{title}</h4>
                <div class="agent-status">✓ Completed</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    left, right, timeline = st.columns([2, 1.5, 1])

    with left:
        st.markdown(f"""
        <div class="glow-card">
            <h3>🚨 Root Cause</h3>
            <p>{root_cause}</p>
            <h4>Evidence</h4>
            <p>{anomaly.replace("#", "").replace("*", "")[:500]}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### AI Confidence")
        st.progress(confidence / 100)
        st.markdown("### 🧠 Why this Root Cause?")

        evidence_points = []

        log_text = logs.lower()

        if "packageextended" in log_text:
            evidence_points.append("✓ Invalid packageExtended attributes detected")

        if "cbs_e_manifest_invalid_item" in log_text:
            evidence_points.append("✓ CBS manifest parsing failure detected")

        if "failed to get next element" in log_text:
            evidence_points.append("✓ Manifest structure validation failed")

        if "sqm" in log_text:
            evidence_points.append("✓ SQM upload failures observed")

        for point in evidence_points:
            st.write(point)

        st.info(
            f"""
            Reasoning Chain:

            {reasoning}

            Conclusion:

            {root_cause}
            """
        )
        st.success(f"{confidence}% confidence based on retrieved context and log evidence")

    with right:
        st.markdown("""
        <div class="glow-card">
            <h3>Recommended Actions</h3>
        </div>
        """, unsafe_allow_html=True)

        for i, action in enumerate(actions, start=1):
            if st.button(f"{i}. {action}", key=f"action_{i}"):
                st.success(f"Executed simulation: {action}")

        st.markdown("---")

        if st.button("🚀 Execute All Actions", type="primary"):
            st.success("All remediation actions simulated successfully.")
            st.code(automation)
            st.info("Ticket updated. Incident marked as mitigated. No real infrastructure was modified.")

    with timeline:
        st.markdown(f"""
        <div class="glow-card">
            <h3>Timeline</h3>
            <div class="timeline-card">🟢 Incident Received</div>
            <div class="timeline-card">🟢 Anomaly Agent Completed</div>
            <div class="timeline-card">🟢 RAG Knowledge Retrieved</div>
            <div class="timeline-card">🟢 RCA Agent Completed</div>
            <div class="timeline-card">🟢 Remediation Agent Completed</div>
            <div class="timeline-card">🟢 Confidence: {confidence}%</div>
            <div class="timeline-card">🟢 Severity: {severity}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("## 💬 AI Copilot")
    report_text = f"""
    AGENTS_026 Incident Diagnosis Report

Root Cause:
{root_cause}

Severity:
{severity}

Confidence:
{confidence}%

Blast Radius:
{blast_radius}

Reasoning:
{reasoning}

Recommended Actions:
{chr(10).join([f"{i+1}. {a}" for i, a in enumerate(actions)])}

Executive Report:
{report}

Automation Plan:
{automation}
"""

    st.download_button(
        label="📄 Download Executive Report",
        data=report_text,
        file_name="incident_diagnosis_report.txt",
        mime="text/plain"
    )

    st.markdown(f"""
    <div class="glow-card">
        <h4 style="color:#c084fc;">AI Assistant</h4>
        <p>{report[:900]}</p>
    </div>
    """, unsafe_allow_html=True)

    user_question = st.text_input(
        "Ask follow-up question about this incident",
        placeholder="Example: Why did this incident happen?"
    )

    if user_question:
        answer = call_llm(
            "You are an SRE Copilot. Answer based only on the incident context.",
            f"""
            Incident Context:
            {report}

            RCA:
        {rca}

Question:
{user_question}
"""
        )
        st.info(answer)

    st.markdown("---")

    st.subheader("📚 Retrieved Knowledge Base Context")

    with st.expander("View Retrieved Context"):
        st.write(st.session_state.get("retrieved_context", "No context retrieved"))

    st.markdown("---")
    st.subheader("Detailed Agent Reasoning")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Anomaly Agent",
        "🧠 Root Cause Agent",
        "🛠 Remediation Agent",
        "🤖 Automation Agent",
        "📄 Executive Report"
    ])

    with tab1:
        st.markdown("### Anomaly Detection Summary")
        st.write(anomaly)

    with tab2:
        st.markdown("### Root Cause Analysis")
        st.write(rca)

    with tab3:
        st.markdown("### Remediation Plan")
        st.write(remediation)

    with tab4:
        st.markdown("### Automation Plan")
        st.write(automation)

    with tab5:
        st.markdown("### Executive Incident Report")
        st.write(report)

        st.download_button(
            "📥 Download Report",
            report,
            file_name="incident_report.txt",
            mime="text/plain"
        )
else:
    st.markdown("""
    <div class="hero-card">
        <h1>🤖 Ready for Incident Diagnosis</h1>
        <p>Paste incident logs and click <b>Run AI Agent Diagnosis</b> to start the multi-agent workflow.</p>
    </div>
    """, unsafe_allow_html=True)