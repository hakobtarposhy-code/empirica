"""
Empirica — Streamlit Web App (v4.3)
"""

import streamlit as st
import os
import sys
import io
import re
import glob
import time
import threading

st.set_page_config(page_title="Empirica", page_icon="📊", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
    .hero-title {
        font-size: 2.8rem; font-weight: 700;
        background: linear-gradient(135deg, #1a1a2e, #555);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem; font-family: 'Space Grotesk', sans-serif;
    }
    .hero-sub { font-size: 1.1rem; color: #888; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">Empirica</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Type a hypothesis. Get a real empirical paper.</div>', unsafe_allow_html=True)

# ── API Key ──────────────────────────────────────────────────────────────────
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

# ── Stage definitions ────────────────────────────────────────────────────────
STAGES = [
    ("🧠", "Parsing hypothesis", "Deciding which World Bank indicators match your variables"),
    ("📊", "Fetching data", "Downloading from the World Bank API for 200+ countries"),
    ("📚", "Searching literature", "Finding related papers on Semantic Scholar and PubMed"),
    ("🔍", "Reviewing data quality", "Checking for outliers, missing data, and cleaning"),
    ("📐", "Running regressions", "OLS with controls, country fixed effects, correlations"),
    ("📊", "Generating charts", "Scatterplot by region and coefficient comparison"),
    ("⚖️", "Interpreting results", "Assessing effect size, direction, and confidence"),
    ("📝", "Writing paper", "Five sections, each grounded in the real statistical output"),
    ("🔎", "Proofreading", "Tightening prose, removing jargon, checking causal claims"),
    ("📄", "Assembling document", "Tables, figures, references, reproduction code"),
]


def detect_stage(log_text):
    checks = [
        ("AGENT 7:", 9),
        ("AGENT 6b: Proofreading", 8),
        ("AGENT 6: Writing", 7),
        ("AGENT 5:", 6),
        ("Generating scatterplot", 5),
        ("Generating coefficient", 5),
        ("AGENT 4:", 4),
        ("AGENT 3:", 3),
        ("AGENT 2b:", 2),
        ("AGENT 2a:", 1),
        ("AGENT 1:", 0),
    ]
    best = -1
    for marker, idx in checks:
        if marker in log_text and idx > best:
            best = idx
    return best


def extract_details(log_text):
    details = {}
    m = re.search(r"-> X: (.+)", log_text)
    if m:
        details["x"] = m.group(1).strip()
    m = re.search(r"-> Y: (.+)", log_text)
    if m:
        details["y"] = m.group(1).strip()
    m = re.search(r"Merged: (\d+) rows, (\d+) countries", log_text)
    if m:
        details["data"] = f"{m.group(1)} observations, {m.group(2)} countries"
    m = re.search(r"(\d+) unique articles found", log_text)
    if m:
        details["lit"] = f"{m.group(1)} papers found"
    return details


# ── Main input ───────────────────────────────────────────────────────────────
hypothesis = st.text_area(
    "Your hypothesis",
    placeholder='e.g., "Higher government healthcare spending leads to longer life expectancy"',
    height=80,
    help="Plain English. Empirica picks the variables, data, and methods.",
)

run_button = st.button("Generate Paper", type="primary")

# ── Execution ────────────────────────────────────────────────────────────────
if run_button:
    if not api_key:
        st.error("Please add your Anthropic API key in the sidebar.")
        st.stop()
    if not hypothesis.strip():
        st.error("Please enter a hypothesis.")
        st.stop()

    os.environ["ANTHROPIC_API_KEY"] = api_key

    try:
        from empirica_v3 import run_empirica
    except ImportError as e:
        st.error(f"Could not import empirica_v3.py: {e}")
        st.stop()

    progress_bar = st.progress(0)
    stage_text = st.empty()
    detail_text = st.empty()

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
            pct = (stage + 1) / len(STAGES)
            progress_bar.progress(pct)
            icon, name, desc = STAGES[stage]
            stage_text.markdown(f"**{icon} {name}** — _{desc}_")

        details = extract_details(log)
        if details:
            parts = []
            if "x" in details:
                parts.append(f"**X →** {details['x']}")
            if "y" in details:
                parts.append(f"**Y →** {details['y']}")
            if "data" in details:
                parts.append(f"**Data:** {details['data']}")
            if "lit" in details:
                parts.append(f"**Literature:** {details['lit']}")
            if parts:
                detail_text.markdown("  \n".join(parts))

    thread.join()
    sys.stdout = old_stdout
    log_text = captured.getvalue()

    progress_bar.empty()
    stage_text.empty()
    detail_text.empty()

    if result_box["error"]:
        st.error(f"Error: {result_box['error']}")
        if log_text:
            with st.expander("Pipeline log (before error)"):
                st.code(log_text, language="text")
        st.info("Check that your API key is valid and has credits at console.anthropic.com")
    else:
        st.success("Paper complete!")

        with st.expander("Pipeline log", expanded=False):
            st.code(log_text, language="text")

        st.divider()
        st.markdown("### Your paper is ready")

        col_a, col_b = st.columns(2)

        paper_path = "output/paper.docx"
        docx_files = glob.glob("output/*.docx") + glob.glob("*.docx")
        actual_paper = paper_path if os.path.exists(paper_path) else (docx_files[0] if docx_files else None)
        if actual_paper:
            with open(actual_paper, "rb") as f:
                col_a.download_button(
                    "📄 Download Paper (.docx)", data=f.read(),
                    file_name="empirica_paper.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        repro_path = "output/reproduce.py"
        py_files = glob.glob("output/*.py")
        actual_repro = repro_path if os.path.exists(repro_path) else (py_files[0] if py_files else None)
        if actual_repro:
            with open(actual_repro, "rb") as f:
                col_b.download_button(
                    "💻 Download Code (.py)", data=f.read(),
                    file_name="reproduce.py", mime="text/x-python",
                    use_container_width=True,
                )

        # Show charts inline
        scatter = "output/scatterplot.png"
        coeff = "output/coefficients.png"
        if os.path.exists(scatter) or os.path.exists(coeff):
            st.divider()
            st.markdown("### Preview")
            if os.path.exists(scatter):
                st.image(scatter, use_container_width=True)
            if os.path.exists(coeff):
                st.image(coeff, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("Empirica doesn't write about research — it does the research. Real data. Real statistics. Real citations.")
