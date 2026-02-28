"""
Empirica — Streamlit Web App
============================
Wraps empirica_v3.py (which uses run_empirica function) into a web interface.

DEPLOY:
    1. Upload this + empirica_v3.py + requirements.txt to GitHub
    2. Go to share.streamlit.io → connect repo → point to app.py
    3. In Advanced Settings → Secrets, add:
         ANTHROPIC_API_KEY = "sk-ant-your-key-here"
    4. Deploy
"""

import streamlit as st
import os
import sys
import io
import glob

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Empirica",
    page_icon="📊",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
    
    .hero-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1a1a2e, #555);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .hero-sub {
        font-size: 1.1rem;
        color: #888;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">Empirica</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Type a hypothesis. Get a real empirical paper.</div>', unsafe_allow_html=True)

# ── API Key handling ─────────────────────────────────────────────────────────
api_key = None

# Try Streamlit secrets first (production on Streamlit Cloud)
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

# Fallback to environment variable
if not api_key:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

# Fallback to sidebar input (local development)
if not api_key:
    with st.sidebar:
        st.markdown("### Setup")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Get one at console.anthropic.com",
        )
        if not api_key:
            st.warning("Add your API key to get started")

# ── Main input ───────────────────────────────────────────────────────────────
hypothesis = st.text_area(
    "Your hypothesis",
    placeholder='e.g., "Higher government healthcare spending leads to longer life expectancy"',
    height=80,
    help="Type in plain English. Empirica figures out the variables, data sources, and methods.",
)

run_button = st.button("Generate Paper", type="primary")

# ── Pipeline execution ───────────────────────────────────────────────────────
if run_button:
    if not api_key:
        st.error("Please add your Anthropic API key in the sidebar.")
        st.stop()

    if not hypothesis.strip():
        st.error("Please enter a hypothesis.")
        st.stop()

    # Set the API key in environment so the pipeline can use it
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # Import the pipeline
    try:
        from empirica_v3 import run_empirica
    except ImportError as e:
        st.error(f"Could not import empirica_v3.py: {e}")
        st.stop()

    # Show progress
    status = st.status("Running Empirica pipeline...", expanded=True)

    # Capture print output so we can show it in the UI
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()

    try:
        with status:
            st.write("Parsing hypothesis with AI...")

            # Run the pipeline — it writes to output/ directory
            run_empirica(hypothesis)

            # Restore stdout and get the log
            sys.stdout = old_stdout
            log_text = captured.getvalue()

        status.update(label="Paper complete!", state="complete")

        # Show the pipeline log in an expander
        with st.expander("Pipeline log", expanded=False):
            st.code(log_text, language="text")

        # ── Find and offer downloads ─────────────────────────────────
        st.divider()
        st.markdown("### Your paper is ready")

        col_a, col_b = st.columns(2)

        # Find the paper
        paper_path = "output/paper.docx"
        docx_files = glob.glob("output/*.docx") + glob.glob("*.docx")
        actual_paper = paper_path if os.path.exists(paper_path) else (docx_files[0] if docx_files else None)

        if actual_paper:
            with open(actual_paper, "rb") as f:
                with col_a:
                    st.download_button(
                        "Download Paper (.docx)",
                        data=f.read(),
                        file_name="empirica_paper.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

        # Find the reproduction script
        repro_path = "output/reproduce.py"
        py_files = glob.glob("output/*.py")
        actual_repro = repro_path if os.path.exists(repro_path) else (py_files[0] if py_files else None)

        if actual_repro:
            with open(actual_repro, "rb") as f:
                with col_b:
                    st.download_button(
                        "Download Code (.py)",
                        data=f.read(),
                        file_name="reproduce.py",
                        mime="text/x-python",
                        use_container_width=True,
                    )

    except Exception as e:
        sys.stdout = old_stdout
        status.update(label="Pipeline failed", state="error")
        st.error(f"Error: {str(e)}")

        # Show what we captured before the error
        log_text = captured.getvalue()
        if log_text:
            with st.expander("Pipeline log (before error)"):
                st.code(log_text, language="text")

        st.info("Check that your API key is valid and has credits at console.anthropic.com")

# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("Empirica doesn't write about research — it does the research. Real data. Real statistics. Real citations.")
