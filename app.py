"""
Empirica — Streamlit App (v4.3)
Faithful port of the React landing page design.
"""

import streamlit as st
import os
import sys
import io
import re
import glob
import time
import threading

st.set_page_config(page_title="Empirica", page_icon="◼", layout="centered", initial_sidebar_state="collapsed")

# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — ported from React/Tailwind
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    .stApp {
        background: #FFFFFF;
        color: #0F172A;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    section[data-testid="stSidebar"] { background: #FAFAFA; }
    .block-container {
        max-width: 800px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

    /* ── Nav / Logo ── */
    .nav {
        display: flex;
        justify-content: center;
        padding: 2rem 0 3rem 0;
    }
    .logo-group {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: default;
    }
    .logo-icon {
        width: 32px; height: 32px;
        background: #0F172A;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .logo-icon span {
        color: white;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 18px;
        line-height: 1;
    }
    .logo-name {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        color: #0F172A;
        letter-spacing: -0.03em;
    }

    /* ── Hero ── */
    .hero-section { text-align: center; padding: 0.5rem 0 2rem 0; }
    .hero-h1 {
        font-family: 'Playfair Display', serif;
        font-size: 4.2rem;
        font-weight: 500;
        color: #0F172A;
        letter-spacing: -0.025em;
        line-height: 1.1;
        margin: 0 0 2rem 0;
    }
    .hero-h1 .accent {
        color: #047857;
        font-style: italic;
    }
    .hero-p {
        font-family: 'Inter', sans-serif;
        font-size: 1.15rem;
        font-weight: 300;
        color: #94A3B8;
        max-width: 520px;
        margin: 0 auto 2.5rem auto;
        line-height: 1.65;
    }

    /* ── Source ticker ── */
    .ticker-block {
        text-align: center;
        margin: 0 auto 0.5rem auto;
    }
    .ticker-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 0.3rem;
    }
    .ticker-window {
        height: 24px;
        overflow: hidden;
        display: flex;
        justify-content: center;
    }
    .ticker-reel {
        display: flex;
        flex-direction: column;
        animation: reel 18s ease-in-out infinite;
    }
    .ticker-reel span {
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 1.05rem;
        color: #047857;
    }
    @keyframes reel {
        0%,5%     { transform: translateY(0); }
        11%,16%   { transform: translateY(-24px); }
        22%,27%   { transform: translateY(-48px); }
        33%,38%   { transform: translateY(-72px); }
        44%,49%   { transform: translateY(-96px); }
        55%,60%   { transform: translateY(-120px); }
        66%,71%   { transform: translateY(-144px); }
        77%,82%   { transform: translateY(-168px); }
        88%,93%   { transform: translateY(-192px); }
        100%      { transform: translateY(0); }
    }

    /* ── Input styling ── */
    .stTextInput > div > div > input {
        background: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        color: #0F172A !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1.1rem !important;
        font-weight: 300 !important;
        padding: 1.3rem 1.4rem !important;
        height: auto !important;
        transition: all 0.25s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #94A3B8 !important;
        background: #FFFFFF !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.04) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #94A3B8 !important;
        font-weight: 300;
    }
    .stTextInput label {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.65rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        color: #94A3B8 !important;
    }

    /* ── Button ── */
    .stButton > button {
        background: #0F172A !important;
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.25s ease !important;
        letter-spacing: -0.01em;
    }
    .stButton > button:hover {
        background: #047857 !important;
        box-shadow: 0 4px 20px rgba(4,120,87,0.18) !important;
        transform: translateY(-1px);
    }

    /* ── Progress bar ── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #047857, #059669) !important;
        border-radius: 6px;
    }
    .stProgress > div { background: #F1F5F9 !important; border-radius: 6px; }

    /* ── Stage card ── */
    .stage-card {
        background: #FFFFFF;
        border: 1px solid #F1F5F9;
        border-radius: 14px;
        padding: 1rem 1.3rem;
        margin: 0.6rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .stage-num {
        font-family: 'Inter', sans-serif;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #CBD5E1;
    }
    .stage-name {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.9rem;
        color: #0F172A;
        margin-top: 0.15rem;
    }
    .stage-desc {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        font-size: 0.82rem;
        color: #94A3B8;
    }

    .detail-readout {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 400;
        color: #64748B;
        padding: 0.3rem 0;
        line-height: 1.9;
    }
    .detail-readout strong {
        color: #334155;
        font-weight: 600;
    }

    /* ── Proof section ── */
    .proof-section {
        background: #F8FAFC;
        border-top: 1px solid #F1F5F9;
        border-bottom: 1px solid #F1F5F9;
        padding: 3rem 0;
        margin: 2.5rem -3rem;
        width: calc(100% + 6rem);
    }
    .proof-grid {
        display: flex;
        gap: 3rem;
        max-width: 700px;
        margin: 0 auto;
        padding: 0 2rem;
    }
    .proof-item { flex: 1; }
    .proof-icon {
        width: 40px; height: 40px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        color: #047857;
    }
    .proof-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 0.85rem;
        color: #0F172A;
        letter-spacing: -0.01em;
    }
    .proof-desc {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        font-size: 0.78rem;
        color: #94A3B8;
        line-height: 1.55;
        margin-top: 0.4rem;
    }

    /* ── Download buttons ── */
    .stDownloadButton > button {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        color: #0F172A !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        border-color: #047857 !important;
        color: #047857 !important;
        box-shadow: 0 2px 12px rgba(4,120,87,0.08) !important;
    }

    /* ── Expander ── */
    details[data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid #F1F5F9 !important;
        border-radius: 12px !important;
    }

    /* ── Misc ── */
    hr { border-color: #F1F5F9 !important; }
    .stCaption p {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.65rem !important;
        color: #CBD5E1 !important;
        text-align: center;
    }
    .stImage { border-radius: 12px; overflow: hidden; border: 1px solid #F1F5F9; }

    /* ── Sidebar ── */
    .stTextInput input {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Footer ── */
    .emp-footer {
        text-align: center;
        padding: 3rem 0 1rem 0;
        border-top: 1px solid #F1F5F9;
    }
    .emp-footer .footer-logo {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 0.6rem;
    }
    .emp-footer .footer-icon {
        width: 24px; height: 24px;
        background: #0F172A;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .emp-footer .footer-icon span {
        color: white;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 12px;
    }
    .emp-footer .footer-name {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 0.9rem;
        color: #0F172A;
        letter-spacing: -0.02em;
    }
    .emp-footer .footer-by {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 600;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 0.4rem;
    }
    .emp-footer .footer-copy {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        color: #CBD5E1;
    }

    /* ── Accent line ── */
    .emerald-line {
        width: 48px; height: 2px;
        background: #047857;
        margin: 0 auto;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #FFF; }
    ::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="nav">
    <div class="logo-group">
        <div class="logo-icon"><span>E</span></div>
        <div class="logo-name">empirica</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-section">
    <h1 class="hero-h1">
        Research,<br><span class="accent">automated.</span>
    </h1>
    <p class="hero-p">
        Turn a single hypothesis into a rigorous, data-backed paper.
        Empirica synthesizes datasets, runs regressions, and drafts
        your manuscript instantly.
    </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE TICKER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="ticker-block">
    <div class="ticker-label">Synthesizing from</div>
    <div class="ticker-window">
        <div class="ticker-reel">
            <span>World Bank</span>
            <span>Semantic Scholar</span>
            <span>PubMed</span>
            <span>Eurostat</span>
            <span>OpenAlex</span>
            <span>RePEc</span>
            <span>SSRN</span>
            <span>Crossref</span>
            <span>Figaro Database</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# API KEY
# ═══════════════════════════════════════════════════════════════════════════════
api_key = None
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass
if not api_key:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    with st.sidebar:
        st.markdown("### Setup")
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        if not api_key:
            st.warning("Add your API key to get started")

# ═══════════════════════════════════════════════════════════════════════════════
# INPUT
# ═══════════════════════════════════════════════════════════════════════════════
hypothesis = st.text_input(
    "hypothesis",
    placeholder="Enter a hypothesis...",
    help="Plain English. Empirica picks the variables, data, and statistical methods.",
)

run_button = st.button("Draft Paper →", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGES
# ═══════════════════════════════════════════════════════════════════════════════
STAGES = [
    ("01", "Parsing hypothesis", "Mapping to World Bank indicator codes"),
    ("02", "Fetching data", "Downloading panel data for 200+ countries"),
    ("03", "Searching literature", "Semantic Scholar and PubMed"),
    ("04", "Reviewing quality", "Outliers, coverage, cleaning"),
    ("05", "Running regressions", "OLS, fixed effects, correlations"),
    ("06", "Generating charts", "Scatterplot and coefficient comparison"),
    ("07", "Interpreting results", "Effect size and confidence"),
    ("08", "Writing paper", "Abstract through conclusion"),
    ("09", "Proofreading", "Tightening prose, verifying claims"),
    ("10", "Assembling document", "Tables, figures, references"),
]

def detect_stage(log_text):
    checks = [
        ("AGENT 7:", 9), ("AGENT 6b:", 8), ("AGENT 6:", 7),
        ("AGENT 5:", 6), ("Generating", 5), ("AGENT 4:", 4),
        ("AGENT 3:", 3), ("AGENT 2b:", 2), ("AGENT 2a:", 1), ("AGENT 1:", 0),
    ]
    best = -1
    for marker, idx in checks:
        if marker in log_text and idx > best:
            best = idx
    return best

def extract_details(log_text):
    d = {}
    m = re.search(r"-> X: (.+)", log_text)
    if m: d["x"] = m.group(1).strip()
    m = re.search(r"-> Y: (.+)", log_text)
    if m: d["y"] = m.group(1).strip()
    m = re.search(r"Merged: (\d+) rows, (\d+) countries", log_text)
    if m: d["data"] = f"{m.group(1)} observations · {m.group(2)} countries"
    m = re.search(r"(\d+) unique articles found", log_text)
    if m: d["lit"] = f"{m.group(1)} papers found"
    return d


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if run_button:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar.")
        st.stop()
    if not hypothesis.strip():
        st.error("Enter a hypothesis.")
        st.stop()

    os.environ["ANTHROPIC_API_KEY"] = api_key

    try:
        from empirica_v3 import run_empirica
    except ImportError as e:
        st.error(f"Import error: {e}")
        st.stop()

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    stage_box = st.empty()
    detail_box = st.empty()

    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    result_box = {"error": None, "done": False}

    def run_pipeline():
        try:
            run_empirica(hypothesis)
        except Exception as e:
            result_box["error"] = str(e)
        finally:
            result_box["done"] = True

    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()

    prev_stage = -1
    while not result_box["done"]:
        time.sleep(0.4)
        log = captured.getvalue()
        stage = detect_stage(log)
        if stage >= 0 and stage != prev_stage:
            prev_stage = stage
            progress_bar.progress((stage + 1) / len(STAGES))
            num, name, desc = STAGES[stage]
            stage_box.markdown(
                f'<div class="stage-card">'
                f'<div class="stage-num">Stage {num} of {len(STAGES)}</div>'
                f'<div class="stage-name">{name}</div>'
                f'<div class="stage-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        details = extract_details(log)
        if details:
            parts = []
            for k, label in [("x","X"), ("y","Y"), ("data","Data"), ("lit","Literature")]:
                if k in details:
                    parts.append(f"<strong>{label}:</strong> {details[k]}")
            if parts:
                detail_box.markdown(
                    f'<div class="detail-readout">{"<br>".join(parts)}</div>',
                    unsafe_allow_html=True,
                )

    thread.join()
    sys.stdout = old_stdout
    log_text = captured.getvalue()

    progress_bar.empty()
    stage_box.empty()
    detail_box.empty()

    if result_box["error"]:
        st.error(f"Pipeline error: {result_box['error']}")
        if log_text:
            with st.expander("Log"):
                st.code(log_text, language="text")
        st.info("Check your API key and credits at console.anthropic.com")
    else:
        st.success("Paper generated.")
        with st.expander("Pipeline log"):
            st.code(log_text, language="text")

        st.markdown('<div style="height:0.8rem"></div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)

        paper_path = "output/paper.docx"
        if os.path.exists(paper_path):
            with open(paper_path, "rb") as f:
                col_a.download_button(
                    "📄 Download Paper", data=f.read(),
                    file_name="empirica_paper.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
        repro_path = "output/reproduce.py"
        if os.path.exists(repro_path):
            with open(repro_path, "rb") as f:
                col_b.download_button(
                    "💻 Download Code", data=f.read(),
                    file_name="reproduce.py", mime="text/x-python",
                    use_container_width=True,
                )

        scatter = "output/scatterplot.png"
        coeff = "output/coefficients.png"
        if os.path.exists(scatter) or os.path.exists(coeff):
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            if os.path.exists(scatter):
                st.image(scatter, use_container_width=True)
            if os.path.exists(coeff):
                st.image(coeff, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PROOF SECTION (only when pipeline hasn't run)
# ═══════════════════════════════════════════════════════════════════════════════
if not run_button or not hypothesis.strip():
    st.markdown("""
    <div class="proof-section">
        <div class="proof-grid">
            <div class="proof-item">
                <div class="proof-icon">📐</div>
                <div class="proof-title">Causal Modeling</div>
                <div class="proof-desc">Automated IV selection and robustness checks powered by global econometric databases.</div>
            </div>
            <div class="proof-item">
                <div class="proof-icon">📝</div>
                <div class="proof-title">Full Manuscripts</div>
                <div class="proof-desc">Intro, Lit Review, and Conclusion drafted in academic tone with reproducible code.</div>
            </div>
            <div class="proof-item">
                <div class="proof-icon">🔗</div>
                <div class="proof-title">Verified Citations</div>
                <div class="proof-desc">Direct links to sources across PubMed, SSRN, and Semantic Scholar.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="emp-footer">
    <div class="footer-logo">
        <div class="footer-icon"><span>E</span></div>
        <span class="footer-name">empirica</span>
    </div>
    <div class="footer-by">Powered by ProdifAI</div>
    <div class="footer-copy">© 2025. Academic research engine.</div>
</div>
""", unsafe_allow_html=True)
