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
        margin-left: auto !important;
        margin-right: auto !important;
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
        gap: 10px;
        cursor: default;
    }
    .logo-name {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.5rem;
        color: #0F172A;
        letter-spacing: -0.04em;
    }

    /* ── Hero ── */
    .hero-section { text-align: center; padding: 0.5rem 0 2rem 0; }
    .hero-h1 {
        font-family: 'Playfair Display', serif;
        font-size: 3.6rem;
        font-weight: 500;
        color: #0F172A;
        letter-spacing: -0.025em;
        line-height: 1.12;
        margin: 0 0 2rem 0;
    }
    .hero-h1 .accent {
        color: #1A6EE0;
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
        color: #1A6EE0;
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
        box-shadow: 0 2px 8px rgba(15,23,42,0.04) !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #94A3B8 !important;
        background: #FFFFFF !important;
        box-shadow: 0 4px 20px rgba(15,23,42,0.06), 0 0 0 3px rgba(0,58,112,0.06) !important;
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
        box-shadow: 0 4px 14px rgba(0,58,112,0.18) !important;
    }
    .stButton > button:hover {
        background: #003A70 !important;
        box-shadow: 0 8px 28px rgba(0,58,112,0.3) !important;
        transform: translateY(-1px);
    }

    /* ── Progress bar ── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #003A70, #2980D4) !important;
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
        box-shadow: 0 4px 12px rgba(15,23,42,0.06);
        color: #003A70;
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
        box-shadow: 0 2px 8px rgba(15,23,42,0.06) !important;
    }
    .stDownloadButton > button:hover {
        border-color: #003A70 !important;
        color: #003A70 !important;
        box-shadow: 0 6px 20px rgba(0,58,112,0.12) !important;
        transform: translateY(-1px);
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
        gap: 8px;
        margin-bottom: 0.6rem;
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
    .mckinsey-line {
        width: 48px; height: 2px;
        background: #003A70;
        margin: 0 auto;
    }

    /* ── Research Console ── */
    .console-wrap {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 12px 40px rgba(15,23,42,0.08), 0 4px 12px rgba(0,58,112,0.05);
        margin: 1rem 0;
        position: relative;
    }
    .console-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.2rem 1.5rem;
        background: #F8FAFC;
        border-bottom: 1px solid #F1F5F9;
        position: relative;
        z-index: 2;
    }
    .console-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .console-engine-icon {
        width: 40px; height: 40px;
        background: #003A70;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(0,58,112,0.3);
        animation: icon-breathe 3s ease-in-out infinite;
        color: white;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        font-size: 18px;
    }
    @keyframes icon-breathe {
        0%, 100% { box-shadow: 0 4px 14px rgba(0,58,112,0.3); }
        50% { box-shadow: 0 4px 24px rgba(0,58,112,0.5); }
    }
    .console-engine-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 0.9rem;
        color: #0F172A;
    }
    .console-engine-hyp {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94A3B8;
    }
    .console-body {
        padding: 2rem 1.5rem;
        position: relative;
        z-index: 2;
    }

    /* ── Floating equations background ── */
    .eq-layer {
        position: absolute;
        inset: 0;
        overflow: hidden;
        pointer-events: none;
        z-index: 1;
    }
    .eq-float {
        position: absolute;
        font-family: 'Playfair Display', serif;
        font-style: italic;
        color: #F1F5F9;
        white-space: nowrap;
        animation: eq-drift linear infinite;
    }
    .eq-float:nth-child(1)  { font-size: 14px; top: 15%; left: -10%; animation-duration: 22s; animation-delay: 0s; }
    .eq-float:nth-child(2)  { font-size: 11px; top: 35%; left: -15%; animation-duration: 28s; animation-delay: 3s; }
    .eq-float:nth-child(3)  { font-size: 16px; top: 55%; left: -20%; animation-duration: 25s; animation-delay: 7s; }
    .eq-float:nth-child(4)  { font-size: 12px; top: 75%; left: -10%; animation-duration: 20s; animation-delay: 2s; }
    .eq-float:nth-child(5)  { font-size: 13px; top: 25%; left: -18%; animation-duration: 30s; animation-delay: 10s; }
    .eq-float:nth-child(6)  { font-size: 10px; top: 65%; left: -12%; animation-duration: 26s; animation-delay: 5s; }
    .eq-float:nth-child(7)  { font-size: 15px; top: 45%; left: -8%;  animation-duration: 24s; animation-delay: 8s; }
    .eq-float:nth-child(8)  { font-size: 11px; top: 85%; left: -14%; animation-duration: 27s; animation-delay: 1s; }
    @keyframes eq-drift {
        0%   { transform: translateX(0); opacity: 0; }
        5%   { opacity: 1; }
        95%  { opacity: 1; }
        100% { transform: translateX(calc(100vw + 200px)); opacity: 0; }
    }

    /* ── Progress inside console ── */
    .console-step-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 0.6rem;
    }
    .console-step-text {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 0.9rem;
        color: #334155;
        overflow: hidden;
        border-right: 2px solid #003A70;
        animation: typewriter-blink 0.8s step-end infinite;
    }
    @keyframes typewriter-blink {
        50% { border-color: transparent; }
    }
    .console-step-pct {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        color: #003A70;
    }

    /* ── Animated progress bar ── */
    .progress-track {
        height: 6px;
        width: 100%;
        background: #F1F5F9;
        border-radius: 4px;
        overflow: hidden;
        position: relative;
    }
    .progress-fill {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #003A70, #2980D4);
        transition: width 0.8s ease;
        position: relative;
    }
    .progress-fill::after {
        content: '';
        position: absolute;
        top: 0; right: 0; bottom: 0;
        width: 40px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: shimmer 1.5s ease-in-out infinite;
    }
    @keyframes shimmer {
        0% { transform: translateX(-40px); }
        100% { transform: translateX(40px); }
    }

    /* ── Animated scatter SVG ── */
    .scatter-anim {
        display: block;
        margin: 1.2rem auto 0 auto;
    }
    .scatter-anim .axis-line {
        stroke: #CBD5E1;
        stroke-width: 1.5;
    }
    .scatter-anim .reg-line {
        stroke: #003A70;
        stroke-width: 2;
        stroke-dasharray: 200;
        stroke-dashoffset: 200;
        animation: draw-line 3s ease forwards;
    }
    @keyframes draw-line {
        to { stroke-dashoffset: 0; }
    }
    .scatter-anim .dot {
        fill: #003A70;
        opacity: 0;
        animation: pop-dot 0.4s ease forwards;
    }
    .scatter-anim .dot:nth-child(3) { animation-delay: 0.3s; }
    .scatter-anim .dot:nth-child(4) { animation-delay: 0.6s; }
    .scatter-anim .dot:nth-child(5) { animation-delay: 0.9s; }
    .scatter-anim .dot:nth-child(6) { animation-delay: 1.2s; }
    .scatter-anim .dot:nth-child(7) { animation-delay: 1.5s; }
    .scatter-anim .dot:nth-child(8) { animation-delay: 1.8s; }
    .scatter-anim .dot:nth-child(9) { animation-delay: 2.1s; }
    .scatter-anim .dot:nth-child(10) { animation-delay: 2.4s; }
    .scatter-anim .dot:nth-child(11) { animation-delay: 2.7s; }
    .scatter-anim .dot:nth-child(12) { animation-delay: 3.0s; }
    .scatter-anim .dot:nth-child(13) { animation-delay: 3.3s; }
    .scatter-anim .dot:nth-child(14) { animation-delay: 3.6s; }
    @keyframes pop-dot {
        0%  { opacity: 0; r: 0; }
        70% { opacity: 1; r: 4.5; }
        100% { opacity: 0.7; r: 3.5; }
    }

    /* ── Economic fact card ── */
    .fact-card {
        background: #F8FAFC;
        border: 1px solid #F1F5F9;
        border-radius: 16px;
        padding: 1.3rem 1.5rem;
        margin-top: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        animation: fact-slide-in 0.6s ease;
    }
    @keyframes fact-slide-in {
        0% { opacity: 0; transform: translateY(10px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .fact-card::after {
        content: '\201C';
        position: absolute;
        top: -10px;
        right: 16px;
        font-family: 'Playfair Display', serif;
        font-size: 80px;
        color: #E8EDF3;
        line-height: 1;
    }
    .fact-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #003A70;
        margin-bottom: 0.5rem;
    }
    .fact-text {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.55;
        position: relative;
        z-index: 1;
    }

    /* ── Console spinner ── */
    .console-spinner {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-top: 1.5rem;
        padding-top: 1rem;
    }
    .console-spinner-text {
        font-family: 'Inter', sans-serif;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94A3B8;
    }
    .console-spinner-dot {
        display: inline-block;
        width: 6px; height: 6px;
        background: #003A70;
        border-radius: 50%;
        animation: console-pulse 1.4s ease-in-out infinite;
    }
    .console-spinner-dot:nth-child(2) { animation-delay: 0.2s; }
    .console-spinner-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes console-pulse {
        0%, 100% { opacity: 0.2; transform: scale(0.8); }
        50% { opacity: 1; transform: scale(1.2); }
    }

    /* ── Detail readout (inside console) ── */
    .console-details {
        font-family: 'Inter', sans-serif;
        font-size: 0.73rem;
        color: #64748B;
        line-height: 1.9;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #F1F5F9;
    }
    .console-details strong {
        color: #334155;
        font-weight: 600;
    }

    /* ── Paper lines animation ── */
    .paper-lines {
        margin-top: 1rem;
        padding: 0.8rem 1rem;
        background: #FDFDFD;
        border: 1px solid #F1F5F9;
        border-radius: 8px;
    }
    .paper-line {
        height: 4px;
        background: #F1F5F9;
        border-radius: 2px;
        margin-bottom: 6px;
        animation: line-fill 2s ease forwards;
        transform-origin: left;
    }
    .paper-line:nth-child(1) { width: 85%; animation-delay: 0.0s; }
    .paper-line:nth-child(2) { width: 92%; animation-delay: 0.3s; }
    .paper-line:nth-child(3) { width: 78%; animation-delay: 0.6s; }
    .paper-line:nth-child(4) { width: 65%; animation-delay: 0.9s; }
    .paper-line:nth-child(5) { width: 88%; animation-delay: 1.2s; }
    @keyframes line-fill {
        0%  { background: #F1F5F9; transform: scaleX(0); }
        50% { background: #D4E2F3; transform: scaleX(1); }
        100% { background: #F1F5F9; transform: scaleX(1); }
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #FFF; }
    ::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 3px; }

    /* ── Manuscript Preview ── */
    .preview-section {
        text-align: center;
        padding: 4rem 0 2rem 0;
    }
    .preview-heading {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 2rem;
    }
    .preview-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 2.5rem 2.5rem 2rem 2.5rem;
        text-align: left;
        box-shadow: 0 8px 32px rgba(15,23,42,0.08), 0 2px 8px rgba(0,58,112,0.04);
        max-width: 640px;
        margin: 0 auto;
        position: relative;
        overflow: hidden;
    }
    .preview-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #003A70, #2980D4, #4A9BE8);
    }
    .preview-card-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.58rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 1rem;
    }
    .preview-card-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.35rem;
        font-weight: 600;
        color: #0F172A;
        line-height: 1.3;
        margin-bottom: 0.4rem;
    }
    .preview-card-meta {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #94A3B8;
        margin-bottom: 1.2rem;
    }
    .preview-card-section-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .preview-card-abstract {
        font-family: 'Playfair Display', serif;
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.65;
        margin-bottom: 1.5rem;
    }
    .preview-card-findings {
        background: #F8FAFC;
        border: 1px solid #F1F5F9;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 6px rgba(15,23,42,0.03);
    }
    .preview-card-findings-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #003A70;
        margin-bottom: 0.6rem;
    }
    .preview-card-finding {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        color: #334155;
        line-height: 1.7;
        padding-left: 1rem;
        position: relative;
        margin-bottom: 0.2rem;
    }
    .preview-card-finding::before {
        content: '→';
        position: absolute;
        left: 0;
        color: #003A70;
        font-weight: 600;
    }
    .preview-card-stats {
        display: flex;
        gap: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid #F1F5F9;
    }
    .preview-card-stat {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #94A3B8;
    }
    .preview-card-stat strong {
        color: #334155;
        font-weight: 600;
    }

    /* ── CTA Button ── */
    .cta-wrap {
        text-align: center;
        padding: 2.5rem 0 1rem 0;
    }
    .cta-btn {
        display: inline-block;
        background: #0F172A;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.85rem 2.5rem;
        border-radius: 14px;
        text-decoration: none;
        transition: all 0.25s ease;
        cursor: pointer;
        border: none;
        box-shadow: 0 4px 14px rgba(0,58,112,0.18);
    }
    .cta-btn:hover {
        background: #003A70;
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0,58,112,0.25);
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="nav">
    <div class="logo-group">
        <svg viewBox="0 0 100 100" width="40" height="40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 35 L50 20 L85 35 L50 50 Z" fill="#0F172A"/>
            <path d="M38 45 V80" stroke="#0F172A" stroke-width="10" stroke-linecap="round"/>
            <path d="M38 62 H65" stroke="#0F172A" stroke-width="8" stroke-linecap="round"/>
            <path d="M38 80 H72" stroke="#0F172A" stroke-width="8" stroke-linecap="round"/>
            <path d="M85 35 V55" stroke="#0F172A" stroke-width="3" stroke-linecap="round" stroke-dasharray="1 4"/>
            <circle cx="85" cy="58" r="4" fill="#0F172A"/>
        </svg>
        <div class="logo-name">empirica</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-section">
    <div style="text-align:center; margin-bottom:1.5rem;">
        <span style="display:inline-block; font-family:'Inter',sans-serif; font-size:0.62rem; font-weight:600; letter-spacing:0.18em; text-transform:uppercase; color:#94A3B8; border:1px solid #E2E8F0; border-radius:20px; padding:0.4rem 1.2rem;">Powered by ProdifAI</span>
    </div>
    <h1 class="hero-h1">
        From Hypothesis to<br>Research Paper <span class="accent">in Seconds</span>
    </h1>
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
# STAGES + CONSOLE LABELS
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

# Fancy console step descriptions
CONSOLE_STEPS = [
    "Decomposing hypothesis into testable variables...",
    "Pulling cross-country panel data from World Bank API...",
    "Scrubbing Semantic Scholar for latent variables...",
    "Running data quality diagnostics...",
    "Estimating OLS with controls and country fixed effects...",
    "Rendering scatterplots and coefficient plots...",
    "Calibrating effect size and confidence intervals...",
    "Synthesizing manuscript sections from statistical output...",
    "Applying McCloskey proofreading rules...",
    "Finalizing document structure and references...",
]

ECONOMIC_FACTS = [
    "Goodhart's Law: When a measure becomes a target, it ceases to be a good measure.",
    "The Lucas Critique argues it is naive to predict the effects of a policy change entirely on the basis of historical data.",
    "The Easterlin Paradox: High income correlates with happiness within a country, but not necessarily across countries over time.",
    "The Resource Curse suggests that countries with abundant natural resources tend to have less economic growth and worse governance.",
    "Okun's Law estimates that for every 1% increase in unemployment, GDP falls by roughly 2%.",
    "The Mundell-Fleming Trilemma: a country cannot simultaneously maintain a fixed exchange rate, free capital movement, and independent monetary policy.",
    "Coase's Theorem: if property rights are well-defined and transaction costs are zero, bargaining will lead to an efficient outcome regardless of the initial allocation.",
    "The Heckscher-Ohlin Model predicts that countries export goods that use their abundant factors of production intensively.",
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

    # Research Console container
    console_container = st.empty()
    detail_container = st.empty()

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
    hyp_short = hypothesis[:50] + "..." if len(hypothesis) > 50 else hypothesis

    while not result_box["done"]:
        time.sleep(0.5)
        log = captured.getvalue()
        stage = detect_stage(log)
        if stage < 0:
            stage = 0

        if stage != prev_stage:
            prev_stage = stage

        pct = int(((stage + 1) / len(STAGES)) * 100)
        step_text = CONSOLE_STEPS[min(stage, len(CONSOLE_STEPS) - 1)]
        fact = ECONOMIC_FACTS[stage % len(ECONOMIC_FACTS)]

        details = extract_details(log)
        detail_html = ""
        if details:
            parts = []
            for k, label in [("x", "X"), ("y", "Y"), ("data", "Data"), ("lit", "Literature")]:
                if k in details:
                    parts.append(f"<strong>{label}:</strong> {details[k]}")
            if parts:
                detail_html = f'<div class="console-details">{"<br>".join(parts)}</div>'

        # Build console HTML with NO indentation (Streamlit treats 4-space indent as code)
        console_html = f'<div class="console-wrap">'
        console_html += '<div class="console-header"><div class="console-header-left">'
        console_html += '<div class="console-engine-icon">E</div>'
        console_html += f'<div><div class="console-engine-title">Empirica Engine v4.3</div>'
        console_html += f'<div class="console-engine-hyp">Analyzing: &quot;{hyp_short}&quot;</div></div>'
        console_html += '</div></div>'
        console_html += '<div class="console-body">'
        console_html += f'<div class="console-step-row"><div class="console-step-text">{step_text}</div><div class="console-step-pct">{pct}%</div></div>'
        console_html += f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
        console_html += f'<div class="fact-card"><div class="fact-label">📖 While you wait</div><div class="fact-text">&ldquo;{fact}&rdquo;</div></div>'
        if detail_html:
            console_html += detail_html
        console_html += '<div class="console-spinner"><span class="console-spinner-dot"></span><span class="console-spinner-dot"></span><span class="console-spinner-dot"></span><span class="console-spinner-text">Neural Synthesis in Progress</span></div>'
        console_html += '</div></div>'
        console_container.markdown(console_html, unsafe_allow_html=True)

    thread.join()
    sys.stdout = old_stdout
    log_text = captured.getvalue()

    console_container.empty()
    detail_container.empty()

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


# ═══════════════════════════════════════════════════════════════════════════════
# PROOF SECTION (only when pipeline hasn't run)
# ═══════════════════════════════════════════════════════════════════════════════
if not run_button or not hypothesis.strip():
    st.markdown("""<div class="proof-section">
<div class="proof-grid">
<div class="proof-item">
<div class="proof-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#003A70" stroke-width="2" stroke-linecap="round"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 6-10"/></svg></div>
<div class="proof-title">Causal Modeling</div>
<div class="proof-desc">Automated IV selection and robustness checks powered by global econometric databases.</div>
</div>
<div class="proof-item">
<div class="proof-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#003A70" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg></div>
<div class="proof-title">Full Manuscripts</div>
<div class="proof-desc">Intro, Lit Review, and Conclusion drafted in academic tone with reproducible code.</div>
</div>
<div class="proof-item">
<div class="proof-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#003A70" stroke-width="2" stroke-linecap="round"><path d="M9 17H7A5 5 0 017 7h2"/><path d="M15 7h2a5 5 0 010 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/></svg></div>
<div class="proof-title">Verified Citations</div>
<div class="proof-desc">Direct links to sources across PubMed, SSRN, and Semantic Scholar.</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

    # ── Manuscript Preview ──
    st.markdown("""<div class="preview-section">
<div class="preview-heading">See what Empirica generates</div>
<div class="preview-card">
<div class="preview-card-label">Generated Research Paper</div>
<div class="preview-card-title">The Impact of Electricity Access on GDP Per Capita: A Cross-Country Analysis</div>
<div class="preview-card-meta">Empirica AI · 2026</div>
<div class="preview-card-section-label">Abstract</div>
<div class="preview-card-abstract">This paper investigates the causal relationship between electricity access and economic output measured by GDP per capita across 142 countries from 1990 to 2023. Using panel data analysis with instrumental variable estimation, we find that a 10 percentage point increase in electricity access is associated with a 4.2% increase in GDP per capita, controlling for institutional quality, education, and trade openness…</div>
<div class="preview-card-findings">
<div class="preview-card-findings-title">Key Findings</div>
<div class="preview-card-finding">Strong positive correlation (r = 0.78) between electricity access and GDP per capita</div>
<div class="preview-card-finding">Effect is strongest in Sub-Saharan Africa and South Asia</div>
<div class="preview-card-finding">Industrial electricity access has 2.3x the impact of residential access alone</div>
</div>
<div class="preview-card-stats">
<div class="preview-card-stat"><strong>12</strong> citations</div>
<div class="preview-card-stat"><strong>3,200</strong> words</div>
<div class="preview-card-stat"><strong>1m 30s</strong> generated</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

    # CTA button — rerun scrolls back to top naturally
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    cta_col = st.columns([1, 2, 1])
    with cta_col[1]:
        if st.button("Try Empirica Free ↑", key="cta_top", use_container_width=True):
            pass  # clicking reruns the app, which loads at top
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""<div class="emp-footer"><div class="footer-logo"><div style="width:28px;height:28px;background:#0F172A;border-radius:5px;display:flex;align-items:center;justify-content:center;color:white;font-family:'Playfair Display',serif;font-weight:700;font-size:14px;">E</div><span class="footer-name">empirica</span></div><div class="footer-by">Powered by ProdifAI</div><div class="footer-copy">&copy; 2026. Academic research engine.</div></div>""", unsafe_allow_html=True)
