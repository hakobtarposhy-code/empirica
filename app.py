"""
Empirica — Streamlit Web App
============================
This file wraps your existing empirica_v3.py pipeline into a web interface.

HOW TO RUN LOCALLY:
    pip install streamlit anthropic pandas statsmodels python-docx requests scipy numpy
    streamlit run app.py

HOW TO DEPLOY (free):
    1. Push this repo to GitHub
    2. Go to share.streamlit.io
    3. Connect your GitHub repo, point to app.py
    4. Add your ANTHROPIC_API_KEY in Settings → Secrets
    5. Done — you get a URL like empirica.streamlit.app
"""

import streamlit as st
import os
import time
import tempfile

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
    
    .stApp {
        background-color: #0a0a0f;
    }
    
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
    }
    
    .hero-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e8e6e1, #888);
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
    
    .step-card {
        background: #12121a;
        border: 1px solid #1e1e2e;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
    
    .step-label {
        font-size: 0.7rem;
        letter-spacing: 3px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    
    .ai-step { color: #f59e0b; }
    .code-step { color: #3b82f6; }
    .done-step { color: #22c55e; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">Empirica</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Type a hypothesis. Get a real empirical paper.</div>', unsafe_allow_html=True)


# ── API Key handling ─────────────────────────────────────────────────────────
# In production (Streamlit Cloud), this comes from Settings → Secrets
# Locally, user can type it in the sidebar
api_key = None

# Try secrets first (production)
if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
    api_key = st.secrets['ANTHROPIC_API_KEY']

# Fallback to environment variable
if not api_key:
    api_key = os.environ.get('ANTHROPIC_API_KEY')

# Fallback to sidebar input (for local dev)
if not api_key:
    with st.sidebar:
        st.markdown("### 🔑 Setup")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Get one at console.anthropic.com"
        )
        if not api_key:
            st.warning("Add your API key to get started")


# ── Main input ───────────────────────────────────────────────────────────────
hypothesis = st.text_area(
    "Your hypothesis",
    placeholder='e.g., "Higher government expenditure on education leads to higher GDP growth"',
    height=80,
    help="Type in plain English. Empirica will figure out the variables, data sources, and analytical methods.",
)

col1, col2 = st.columns([1, 3])
with col1:
    run_button = st.button("🔬 Generate Paper", type="primary", use_container_width=True)


# ── Pipeline execution ───────────────────────────────────────────────────────
if run_button:
    if not api_key:
        st.error("Please add your Anthropic API key in the sidebar.")
        st.stop()
    
    if not hypothesis.strip():
        st.error("Please enter a hypothesis.")
        st.stop()
    
    # Set the key for the pipeline
    os.environ['ANTHROPIC_API_KEY'] = api_key
    
    # Import your existing pipeline
    # NOTE: This imports from empirica_v3.py which should be in the same directory
    try:
        from empirica_v3 import EmpiriCA
    except ImportError:
        st.error(
            "Could not import empirica_v3.py. "
            "Make sure it's in the same directory as app.py."
        )
        st.stop()
    
    # ── Run the pipeline with live progress updates ──────────────────────
    progress_bar = st.progress(0)
    status_area = st.empty()
    
    steps = [
        ("🧠 Parsing hypothesis with AI...", "ai-step", 0.05),
        ("📊 Fetching World Bank data...", "code-step", 0.15),
        ("📚 Searching Semantic Scholar + PubMed...", "code-step", 0.30),
        ("🔍 AI reviewing data quality...", "ai-step", 0.40),
        ("📈 Running statistical analysis...", "code-step", 0.55),
        ("⚖️ AI interpreting results...", "ai-step", 0.65),
        ("📝 AI writing paper sections...", "ai-step", 0.75),
        ("📄 Assembling document...", "code-step", 0.95),
    ]
    
    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            engine = EmpiriCA(output_dir=tmpdir)
            
            # Hook into the pipeline steps
            # NOTE: You'll need to add callback support to empirica_v3.py
            # For now, we simulate progress. See the README for how to add real callbacks.
            
            # Run the actual pipeline
            step_idx = 0
            
            def update_progress(step_name):
                """Call this from within the pipeline to update the UI."""
                nonlocal step_idx
                if step_idx < len(steps):
                    label, css_class, pct = steps[step_idx]
                    progress_bar.progress(pct)
                    status_area.markdown(
                        f'<div class="step-card"><span class="step-label {css_class}">{label}</span></div>',
                        unsafe_allow_html=True
                    )
                    step_idx += 1
            
            # Run pipeline
            # Option A: If your pipeline supports callbacks
            # result = engine.run(hypothesis, progress_callback=update_progress)
            
            # Option B: Simple version — just run and show final progress
            for label, css_class, pct in steps:
                progress_bar.progress(pct)
                status_area.markdown(
                    f'<div class="step-card"><span class="step-label {css_class}">{label}</span></div>',
                    unsafe_allow_html=True
                )
            
            result = engine.run(hypothesis)
            
            progress_bar.progress(1.0)
            status_area.markdown(
                '<div class="step-card"><span class="step-label done-step">✅ PAPER COMPLETE</span></div>',
                unsafe_allow_html=True
            )
            
            # ── Show results ─────────────────────────────────────────────
            st.divider()
            st.markdown("### 📄 Your paper is ready")
            
            # Download buttons
            col_a, col_b = st.columns(2)
            
            paper_path = os.path.join(tmpdir, "paper.docx")
            repro_path = os.path.join(tmpdir, "reproduce.py")
            
            if os.path.exists(paper_path):
                with open(paper_path, "rb") as f:
                    with col_a:
                        st.download_button(
                            "📥 Download Paper (.docx)",
                            data=f.read(),
                            file_name="empirica_paper.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
            
            if os.path.exists(repro_path):
                with open(repro_path, "rb") as f:
                    with col_b:
                        st.download_button(
                            "💻 Download Code (.py)",
                            data=f.read(),
                            file_name="reproduce.py",
                            mime="text/x-python",
                            use_container_width=True,
                        )
            
            # Show summary stats if available
            if hasattr(result, 'stats_summary'):
                with st.expander("📊 Analysis Summary"):
                    st.json(result.stats_summary)
        
        except Exception as e:
            progress_bar.empty()
            status_area.empty()
            st.error(f"Pipeline error: {str(e)}")
            st.info("Check that your API key is valid and has credits at console.anthropic.com")


# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<div style="text-align:center; color:#555; font-size:0.8rem;">'
    'Empirica doesn\'t write about research — it does the research.<br>'
    'Real data · Real statistics · Real citations'
    '</div>',
    unsafe_allow_html=True,
)
