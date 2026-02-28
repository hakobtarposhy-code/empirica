# ============================================================================
# EMPIRICA v4.1 — Complete Research Pipeline
# ============================================================================
# Deployment-ready. No hardcoded API keys. No Colab-specific code.
#
# Usage:
#   As module (from Streamlit/app.py):
#       from empirica_v3 import run_empirica
#       run_empirica("Your hypothesis here")
#
#   As standalone script:
#       export ANTHROPIC_API_KEY=sk-ant-your-key
#       python empirica_v3.py "Your hypothesis here"
# ============================================================================

import os
import sys
import json
import re
import time
import warnings
from datetime import datetime

import requests
import numpy as np
import pandas as pd
import scipy.stats as scipystats
import statsmodels.api as sm
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import anthropic

warnings.filterwarnings("ignore")


# ============================================================================
# CONFIGURATION
# ============================================================================
CLAUDE_MODEL = "claude-sonnet-4-20250514"
OUTPUT_DIR = "output"

INDICATOR_FAMILIES = {
    "NY.GDP": "GDP",
    "SE.XPD": "Education spending",
    "SH.XPD": "Health spending",
    "SP.DYN": "Demographics",
    "SI.POV": "Poverty",
}


# ============================================================================
# CLAUDE API HELPERS
# ============================================================================
def get_claude_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set.")
    return anthropic.Anthropic(api_key=api_key)


def ask_claude(system: str, user: str, max_tokens: int = 4000) -> str:
    client = get_claude_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def ask_claude_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    raw = ask_claude(system, user, max_tokens)
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from Claude response:\n{raw[:500]}")


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    text = re.sub(r"\$(.+?)\$", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_duplicate_heading(text: str, heading: str) -> str:
    """Remove duplicate heading at the start of AI-generated section text."""
    lines = text.strip().split("\n")
    if not lines:
        return text
    first = lines[0].strip().lower()
    heading_clean = heading.strip().lower()
    # Remove leading numbers like "1." "2." etc
    first_no_num = re.sub(r"^\d+[\.\)]\s*", "", first)
    heading_no_num = re.sub(r"^\d+[\.\)]\s*", "", heading_clean)
    if first_no_num == heading_no_num or first == heading_no_num:
        return "\n".join(lines[1:]).strip()
    return text


# ============================================================================
# REGION MAPPING (for colored scatterplots)
# ============================================================================
def fetch_country_regions() -> dict:
    """Fetch country-to-region mapping from World Bank API."""
    try:
        resp = requests.get(
            "https://api.worldbank.org/v2/country?format=json&per_page=300",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 2:
            return {}
        mapping = {}
        for c in data[1]:
            code = c.get("id", "")
            region = c.get("region", {}).get("value", "Other")
            name = c.get("name", "")
            if region and region != "Aggregates":
                mapping[name] = region
        return mapping
    except Exception:
        return {}


REGION_COLORS = {
    "East Asia & Pacific": "#E63946",
    "Europe & Central Asia": "#457B9D",
    "Latin America & Caribbean": "#2A9D8F",
    "Middle East & North Africa": "#E9C46A",
    "North America": "#264653",
    "South Asia": "#F4A261",
    "Sub-Saharan Africa": "#6A0572",
    "Other": "#AAAAAA",
}


# ============================================================================
# CHART GENERATION (ggplot-style)
# ============================================================================
def setup_ggplot_style():
    """Configure matplotlib to look like ggplot2."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#F0F0F0",
        "axes.grid": True,
        "grid.color": "white",
        "grid.linewidth": 1.2,
        "axes.edgecolor": "#CCCCCC",
        "axes.linewidth": 0.8,
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.dpi": 150,
    })


def generate_scatterplot(df: pd.DataFrame, plan: dict, output_dir: str) -> str:
    """Generate a ggplot-style scatterplot colored by region."""
    setup_ggplot_style()
    print("  📊 Generating scatterplot...")

    regions = fetch_country_regions()
    df_plot = df.copy()
    df_plot["region"] = df_plot["country"].map(regions).fillna("Other")

    # Aggregate to country means for cleaner plot
    country_means = df_plot.groupby(["country", "region"]).agg(
        x=("x", "mean"), y=("y", "mean")
    ).reset_index()

    fig, ax = plt.subplots(figsize=(8, 5.5))

    for region, color in REGION_COLORS.items():
        subset = country_means[country_means["region"] == region]
        if len(subset) > 0:
            ax.scatter(
                subset["x"], subset["y"],
                c=color, label=region, alpha=0.7, s=35, edgecolors="white", linewidths=0.4,
            )

    # Regression line
    valid = country_means.dropna(subset=["x", "y"])
    if len(valid) > 2:
        z = np.polyfit(valid["x"], valid["y"], 1)
        p = np.poly1d(z)
        x_line = np.linspace(valid["x"].min(), valid["x"].max(), 100)
        ax.plot(x_line, p(x_line), color="#333333", linewidth=1.5, linestyle="--", alpha=0.7)

    ax.set_xlabel(plan["x_label"])
    ax.set_ylabel(plan["y_label"])
    ax.set_title(f"{plan['x_label']} vs {plan['y_label']}", fontweight="bold")
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#CCCCCC", ncol=2)

    plt.tight_layout()
    path = os.path.join(output_dir, "scatterplot.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    ✅ Saved: {path}")
    return path


def generate_coefficient_plot(results: dict, plan: dict, output_dir: str) -> str:
    """Generate a coefficient comparison plot across specifications."""
    setup_ggplot_style()
    print("  📊 Generating coefficient plot...")

    specs = []
    labels = []

    if "ols_controls" in results and "error" not in results["ols_controls"]:
        r = results["ols_controls"]
        specs.append((r["coefficient"], r["std_error"], r["p_value"]))
        labels.append("OLS + Controls")

    if "fixed_effects" in results and "error" not in results["fixed_effects"]:
        r = results["fixed_effects"]
        specs.append((r["coefficient"], r["std_error"], r["p_value"]))
        labels.append("Fixed Effects")

    if not specs:
        # Fallback to simple OLS
        if "ols" in results and "error" not in results["ols"]:
            r = results["ols"]
            specs.append((r["coefficient"], r["std_error"], r["p_value"]))
            labels.append("OLS")

    if not specs:
        return ""

    fig, ax = plt.subplots(figsize=(6, max(2.5, len(specs) * 1.2)))

    y_pos = range(len(specs))
    coefs = [s[0] for s in specs]
    errors = [s[1] * 1.96 for s in specs]  # 95% CI
    colors = ["#2A9D8F" if s[2] < 0.05 else "#E76F51" for s in specs]

    ax.barh(y_pos, coefs, xerr=errors, color=colors, alpha=0.8, height=0.5,
            edgecolor="white", capsize=4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="-")
    ax.set_xlabel(f"Effect on {plan['y_label']}")
    ax.set_title("Coefficient Estimates (95% CI)", fontweight="bold")

    # Color legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2A9D8F", label="p < 0.05"),
        Patch(facecolor="#E76F51", label="p ≥ 0.05"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True, facecolor="white")

    plt.tight_layout()
    path = os.path.join(output_dir, "coefficients.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    ✅ Saved: {path}")
    return path


# ============================================================================
# TAUTOLOGY GUARD (v4.2 — dynamic)
# ============================================================================
def check_tautology(x_code: str, y_code: str) -> bool:
    """Check if X and Y are from the same indicator family."""
    if x_code == y_code:
        return True
    # Check hardcoded families
    for prefix in INDICATOR_FAMILIES:
        if x_code.startswith(prefix) and y_code.startswith(prefix):
            return True
    # Dynamic check: if the first two segments match (e.g., SI.POV.xxx and SI.POV.yyy)
    x_parts = x_code.split(".")
    y_parts = y_code.split(".")
    if len(x_parts) >= 2 and len(y_parts) >= 2:
        if x_parts[0] == y_parts[0] and x_parts[1] == y_parts[1]:
            return True
    return False


# ============================================================================
# INDICATOR VALIDATION (v4.2 — new)
# ============================================================================
def validate_indicator(indicator: str) -> dict:
    """Check if a World Bank indicator exists and has data. Returns info dict or None."""
    try:
        resp = requests.get(
            f"https://api.worldbank.org/v2/indicator/{indicator}?format=json",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) >= 2 and data[1]:
            info = data[1][0]
            return {
                "id": info.get("id", ""),
                "name": info.get("name", ""),
                "source": info.get("source", {}).get("value", ""),
            }
    except Exception:
        pass
    return None


def check_data_availability(indicator: str, start_year: int = 2000, end_year: int = 2023) -> int:
    """Quick check: how many data points does this indicator have? Returns count."""
    try:
        resp = requests.get(
            f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
            f"?date={start_year}:{end_year}&format=json&per_page=1&page=1",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) >= 1 and isinstance(data[0], dict):
            return data[0].get("total", 0)
    except Exception:
        pass
    return 0


def search_wb_indicators(keyword: str, max_results: int = 5) -> list:
    """Search World Bank for indicators matching a keyword."""
    try:
        resp = requests.get(
            f"https://api.worldbank.org/v2/indicator?format=json&per_page=100",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 2 or not data[1]:
            return []
        # Filter by keyword in name
        kw = keyword.lower()
        matches = []
        for ind in data[1]:
            name = ind.get("name", "").lower()
            if kw in name:
                matches.append({
                    "code": ind["id"],
                    "name": ind["name"],
                })
        return matches[:max_results]
    except Exception:
        return []


def validate_and_fix_indicators(plan: dict) -> dict:
    """Validate all indicators in the plan and fix any that are invalid or sparse."""
    print("  🔍 Validating indicators...")

    for var_key, label_key in [("independent_var", "x_label"), ("dependent_var", "y_label")]:
        code = plan[var_key]
        info = validate_indicator(code)

        if not info:
            print(f"    ⚠️  {code} does not exist in World Bank!")
            # Ask Claude to suggest an alternative
            alt = ask_claude_json(
                system="You are a World Bank data expert. Suggest a VALID World Bank indicator code. Return JSON: {\"code\": \"XX.XXX.XXX\", \"name\": \"description\"}",
                user=f"The indicator {code} ({plan[label_key]}) does not exist. Suggest a valid alternative that measures the same concept.",
            )
            plan[var_key] = alt.get("code", code)
            plan[label_key] = alt.get("name", plan[label_key])
            print(f"    ✅ Replaced with: {plan[var_key]} ({plan[label_key]})")
        else:
            # Check data availability
            count = check_data_availability(code, plan.get("start_year", 2000), plan.get("end_year", 2023))
            if count < 200:
                print(f"    ⚠️  {code} has very sparse data ({count} points). Asking AI for denser alternative...")
                alt = ask_claude_json(
                    system="""You are a World Bank data expert. The user needs an indicator with GOOD data coverage (most countries, most years).
Suggest a VALID World Bank indicator that measures the same concept but has better data availability.
Common well-populated indicators include:
- NY.GDP.PCAP.PP.KD, NY.GDP.MKTP.KD.ZG, SP.DYN.LE00.IN, SP.DYN.IMRT.IN
- SE.XPD.TOTL.GD.ZS, SH.XPD.CHEX.GD.ZS, IT.NET.USER.ZS, SP.URB.TOTL.IN.ZS
- SL.UEM.TOTL.ZS, FP.CPI.TOTL.ZG, SP.POP.GROW, EG.ELC.ACCS.ZS
Return JSON: {"code": "XX.XXX.XXX", "name": "description", "reasoning": "why this is better"}""",
                    user=f"Indicator {code} ({plan[label_key]}) has only {count} data points (very sparse). I need something that measures '{plan[label_key]}' but with much better coverage across countries and years.",
                )
                new_code = alt.get("code", code)
                new_count = check_data_availability(new_code, plan.get("start_year", 2000), plan.get("end_year", 2023))
                if new_count > count:
                    plan[var_key] = new_code
                    plan[label_key] = alt.get("name", plan[label_key])
                    print(f"    ✅ Switched to: {new_code} ({plan[label_key]}) — {new_count} data points")
                else:
                    print(f"    ℹ️  Keeping {code} — alternative wasn't better")
            else:
                print(f"    ✅ {code} — {count} data points (good)")

    return plan


# ============================================================================
# AGENT 1: HYPOTHESIS PARSER (AI)
# ============================================================================
def ai_parse_hypothesis(hypothesis_text: str) -> dict:
    print("\n🧠 AGENT 1: Parsing hypothesis with AI...")

    plan = ask_claude_json(
        system="""You are a research methodology expert with deep knowledge of the World Bank's data catalog (16,000+ indicators).

Given a hypothesis, pick the BEST World Bank indicator codes for X (cause) and Y (effect).

CRITICAL RULES:
1. X and Y MUST be from DIFFERENT domains — never two GDP indicators, two health indicators, etc.
2. The relationship must be CAUSAL/INTERESTING, not an accounting identity
3. PREFER indicators with GOOD data coverage — most countries, most years (2000-2023)
4. Pick 2-4 control variables that are CONFOUNDERS
5. You know thousands of World Bank indicator codes from your training — use ANY valid one

WELL-POPULATED indicators (prefer these when possible):
GDP: NY.GDP.PCAP.PP.KD, NY.GDP.MKTP.KD.ZG, NY.GDP.PCAP.KD.ZG
Trade: NE.EXP.GNFS.ZS, NE.IMP.GNFS.ZS, TG.VAL.TOTL.GD.ZS
Finance: FP.CPI.TOTL.ZG, FM.LBL.BMNY.GD.ZS, BX.KLT.DINV.WD.GD.ZS
Education: SE.XPD.TOTL.GD.ZS, SE.SEC.ENRR, SE.TER.ENRR, SE.PRM.ENRR
Health: SH.XPD.CHEX.GD.ZS, SP.DYN.LE00.IN, SP.DYN.IMRT.IN, SH.MED.PHYS.ZS
Infrastructure: IT.NET.USER.ZS, EG.ELC.ACCS.ZS, IT.CEL.SETS.P2
Demographics: SP.URB.TOTL.IN.ZS, SP.POP.GROW, SP.DYN.TFRT.IN
Labor: SL.UEM.TOTL.ZS, SL.TLF.CACT.ZS, SL.AGR.EMPL.ZS
Governance: GE.EST, CC.EST, RL.EST, VA.EST
Environment: EN.ATM.CO2E.PC, EG.USE.ELEC.KH.PC, AG.LND.FRST.ZS
Poverty: SI.POV.DDAY (note: SI.POV.GINI has VERY sparse data — avoid it)
Water/Sanitation: SH.H2O.SMDW.ZS, SH.STA.SMSS.ZS

But you are NOT limited to this list. Use any valid World Bank indicator code you know.
If the hypothesis involves a niche topic (e.g., renewable energy, military spending, tourism),
use the appropriate specialized indicator.

Return JSON:
{
    "title": "Academic paper title (specific, not generic)",
    "statement": "Cleaned hypothesis",
    "independent_var": "World Bank indicator code for X (the CAUSE)",
    "dependent_var": "World Bank indicator code for Y (the EFFECT)",
    "x_label": "Human-readable label for X",
    "y_label": "Human-readable label for Y",
    "control_vars": [
        {"code": "indicator code", "label": "label", "rationale": "why"}
    ],
    "start_year": 2000,
    "end_year": 2023,
    "pubmed_query": "search query for PubMed",
    "semantic_scholar_query": "search query for Semantic Scholar",
    "reasoning": "why these indicators are the best choice"
}""",
        user=f'Hypothesis: "{hypothesis_text}"\n\nPick the BEST indicators. Prefer well-populated ones. X = CAUSE, Y = EFFECT.',
    )

    # Tautology check (v4.1)
    if check_tautology(plan["independent_var"], plan["dependent_var"]):
        print(f"  ⚠️  TAUTOLOGY DETECTED: {plan['independent_var']} -> {plan['dependent_var']}")

        h = hypothesis_text.lower()
        if "health" in h and ("life expectancy" in h or "mortality" in h or "life" in h):
            plan["independent_var"] = "SH.XPD.CHEX.GD.ZS"
            plan["dependent_var"] = "SP.DYN.LE00.IN"
            plan["x_label"] = "Current health expenditure (% of GDP)"
            plan["y_label"] = "Life expectancy at birth (years)"
        elif "education" in h and ("gdp" in h or "growth" in h or "income" in h):
            plan["independent_var"] = "SE.XPD.TOTL.GD.ZS"
            plan["dependent_var"] = "NY.GDP.PCAP.PP.KD"
            plan["x_label"] = "Government expenditure on education (% of GDP)"
            plan["y_label"] = "GDP per capita (PPP, constant 2017 $)"
        elif "internet" in h and ("gdp" in h or "growth" in h or "income" in h):
            plan["independent_var"] = "IT.NET.USER.ZS"
            plan["dependent_var"] = "NY.GDP.PCAP.PP.KD"
            plan["x_label"] = "Individuals using the Internet (% of population)"
            plan["y_label"] = "GDP per capita (PPP, constant 2017 $)"

        print(f"  ✅ Corrected to: {plan['x_label']} -> {plan['y_label']}")

    # Control variable check
    if len(plan.get("control_vars", [])) < 2:
        default_controls = [
            {"code": "NY.GDP.PCAP.PP.KD", "label": "GDP per capita (PPP)", "rationale": "Income level confounder"},
            {"code": "SE.SEC.ENRR", "label": "Secondary school enrollment", "rationale": "Education confounder"},
            {"code": "SP.URB.TOTL.IN.ZS", "label": "Urban population (%)", "rationale": "Urbanization confounder"},
        ]
        existing_codes = {c["code"] for c in plan.get("control_vars", [])}
        for dc in default_controls:
            if dc["code"] not in existing_codes and dc["code"] != plan["independent_var"] and dc["code"] != plan["dependent_var"]:
                plan.setdefault("control_vars", []).append(dc)
                if len(plan["control_vars"]) >= 3:
                    break

    print(f"  -> Title: {plan['title']}")
    print(f"  -> X: {plan['x_label']} ({plan['independent_var']})")
    print(f"  -> Y: {plan['y_label']} ({plan['dependent_var']})")
    print(f"  -> Controls: {', '.join(c['label'] for c in plan['control_vars'])}")
    print(f"  -> Years: {plan['start_year']}-{plan['end_year']}")

    # Validate indicators exist and have enough data (v4.2)
    plan = validate_and_fix_indicators(plan)

    return plan


# ============================================================================
# AGENT 2: DATA COLLECTOR (Code)
# ============================================================================
class WorldBankFetcher:
    BASE_URL = "https://api.worldbank.org/v2"

    AGGREGATES = {
        "WLD", "HIC", "LIC", "LMC", "MIC", "UMC", "LMY", "HPC",
        "EAS", "ECS", "LCN", "MEA", "NAC", "SAS", "SSF", "AFE",
        "AFW", "ARB", "CEB", "CSS", "EAP", "EAR", "EMU", "EUU",
        "FCS", "IDA", "IDX", "LAC", "LDC", "LTE", "MNA", "OED",
        "OSS", "PRE", "PSS", "PST", "SSA", "SST", "TEA", "TEC",
        "TLA", "TMN", "TSA", "TSS", "IBD", "IBT", "IDB",
    }

    def fetch(self, indicator: str, start_year: int, end_year: int) -> pd.DataFrame:
        print(f"  📊 Fetching {indicator} ({start_year}-{end_year})...")
        all_data = []
        page = 1
        while True:
            url = (
                f"{self.BASE_URL}/country/all/indicator/{indicator}"
                f"?date={start_year}:{end_year}&format=json&per_page=1000&page={page}"
            )
            # Retry up to 3 times per page
            resp_data = None
            for attempt in range(3):
                try:
                    resp = requests.get(url, timeout=45)
                    resp.raise_for_status()
                    resp_data = resp.json()
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"    ⚠️  Retry {attempt + 1}/3 for {indicator}: {e}")
                        time.sleep(2)
                    else:
                        print(f"    ⚠️  World Bank API failed after 3 attempts: {e}")

            if not resp_data:
                break

            if len(resp_data) < 2 or not resp_data[1]:
                break

            for record in resp_data[1]:
                value = record.get("value")
                if value is not None:
                    cc = record.get("country", {}).get("id", "")
                    if cc not in self.AGGREGATES:
                        all_data.append({
                            "country": record["country"]["value"],
                            "country_code": cc,
                            "year": int(record["date"]),
                            "value": float(value),
                        })

            if page >= resp_data[0].get("pages", 1):
                break
            page += 1

        df = pd.DataFrame(all_data)
        if not df.empty:
            print(f"    ✅ {len(df)} observations, {df['country'].nunique()} countries")
        else:
            print(f"    ⚠️  No data returned for {indicator}")
        return df


class SemanticScholarSearcher:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def search(self, query: str, max_results: int = 8) -> list:
        papers = []
        for attempt in range(3):
            try:
                print(f"  📖 Semantic Scholar (attempt {attempt + 1}): {query}")
                resp = requests.get(
                    f"{self.BASE_URL}/paper/search",
                    params={
                        "query": query, "limit": max_results,
                        "fields": "title,authors,year,journal,externalIds,abstract,citationCount",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                papers = resp.json().get("data", [])
                if papers:
                    break
            except Exception as e:
                print(f"    -> Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)
                papers = []

        articles = []
        for p in papers:
            try:
                title = p.get("title", "")
                authors_raw = p.get("authors", [])
                authors = [a.get("name", "") for a in authors_raw if a.get("name")]
                year = str(p.get("year", ""))
                if not (title and authors and year and year != "None"):
                    continue
                journal_info = p.get("journal")
                journal = journal_info.get("name", "Unknown") if journal_info else "Unknown"
                ext_ids = p.get("externalIds", {}) or {}
                doi = ext_ids.get("DOI", "")
                abstract = (p.get("abstract") or "")[:500]
                citations = p.get("citationCount", 0) or 0
                authors_short = f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)
                articles.append({
                    "title": title, "authors": authors, "authors_short": authors_short,
                    "year": year, "journal": journal, "doi": doi, "pmid": "",
                    "abstract": abstract, "citations": citations, "source": "Semantic Scholar",
                })
                print(f"    -> {authors_short} ({year}) [{citations} cites] - {title[:60]}...")
            except Exception:
                continue
        articles.sort(key=lambda a: a.get("citations", 0), reverse=True)
        return articles


class PubMedSearcher:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search(self, query: str, max_results: int = 5) -> list:
        print(f"  📖 PubMed search: {query}")
        try:
            search_resp = requests.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params={"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json", "sort": "relevance"},
                timeout=15,
            )
            search_resp.raise_for_status()
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                print("    ⚠️  No PubMed results")
                return []

            fetch_resp = requests.get(
                f"{self.BASE_URL}/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
                timeout=15,
            )
            fetch_resp.raise_for_status()
            results = fetch_resp.json().get("result", {})

            articles = []
            for pmid in ids:
                info = results.get(pmid, {})
                if not info or pmid == "uids":
                    continue
                title = info.get("title", "").rstrip(".")
                authors_raw = info.get("authors", [])
                authors = [a.get("name", "") for a in authors_raw if a.get("name")]
                if not authors:
                    continue
                year = info.get("pubdate", "")[:4]
                journal = info.get("source", "Unknown")
                doi_list = [x.get("value", "") for x in info.get("articleids", []) if x.get("idtype") == "doi"]
                doi = doi_list[0] if doi_list else ""
                authors_short = f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)
                articles.append({
                    "title": title, "authors": authors, "authors_short": authors_short,
                    "year": year, "journal": journal, "doi": doi, "pmid": pmid,
                    "abstract": "", "citations": 0, "source": "PubMed",
                })
                print(f"    -> {authors_short} ({year}) - {title[:60]}...")
            return articles
        except Exception as e:
            print(f"    ⚠️  PubMed error: {e}")
            return []


class LiteratureSearcher:
    def __init__(self):
        self.ss = SemanticScholarSearcher()
        self.pm = PubMedSearcher()

    def search(self, ss_query: str, pm_query: str) -> list:
        print("\n📚 AGENT 2b: Searching literature...")
        ss_results = self.ss.search(ss_query)
        time.sleep(1)
        pm_results = self.pm.search(pm_query)

        seen_dois = set()
        combined = []
        for article in ss_results + pm_results:
            doi = article.get("doi", "")
            if doi and doi in seen_dois:
                continue
            if doi:
                seen_dois.add(doi)
            combined.append(article)

        combined.sort(key=lambda a: a.get("citations", 0), reverse=True)
        print(f"  ✅ {len(combined)} unique articles found")
        return combined


# ============================================================================
# AGENT 3: DATA REVIEWER (AI)
# ============================================================================
def ai_review_data(df: pd.DataFrame, plan: dict) -> dict:
    print("\n🔍 AGENT 3: AI reviewing data quality...")

    summary = {
        "rows": len(df),
        "countries": int(df["country"].nunique()) if "country" in df.columns else 0,
        "years": f"{int(df['year'].min())}-{int(df['year'].max())}" if "year" in df.columns else "N/A",
    }
    for col in ["x", "y"]:
        if col in df.columns:
            summary[f"{col}_stats"] = {
                "mean": round(float(df[col].mean()), 4),
                "std": round(float(df[col].std()), 4),
                "min": round(float(df[col].min()), 4),
                "max": round(float(df[col].max()), 4),
                "missing_pct": round(float(df[col].isna().mean() * 100), 2),
                "zeros_pct": round(float((df[col] == 0).mean() * 100), 2),
            }

    review = ask_claude_json(
        system="""You are a data quality analyst. Review this dataset and recommend cleaning.
Return JSON:
{
    "assessment": "brief quality assessment",
    "winsorize": true/false,
    "winsorize_percentile": 1 or 5,
    "exclude_zeros_x": true/false,
    "exclude_zeros_y": true/false,
    "min_observations_per_country": 3 or 5,
    "exclude_countries": [],
    "warnings": []
}""",
        user=f"Hypothesis: {plan['statement']}\n\n{json.dumps(summary, indent=2)}",
    )

    print(f"  -> Assessment: {review.get('assessment', 'N/A')}")
    for w in review.get("warnings", []):
        print(f"  ⚠️  {w}")
    return review


def apply_cleaning(df: pd.DataFrame, review: dict) -> pd.DataFrame:
    print("  🧹 Applying cleaning...")
    original_len = len(df)

    if review.get("winsorize", False):
        pct = review.get("winsorize_percentile", 1) / 100
        for col in ["x", "y"]:
            if col in df.columns:
                df[col] = df[col].clip(df[col].quantile(pct), df[col].quantile(1 - pct))

    if review.get("exclude_zeros_x") and "x" in df.columns:
        df = df[df["x"] != 0]
    if review.get("exclude_zeros_y") and "y" in df.columns:
        df = df[df["y"] != 0]

    min_obs = review.get("min_observations_per_country", 3)
    if "country" in df.columns:
        counts = df.groupby("country").size()
        df = df[df["country"].isin(counts[counts >= min_obs].index)]

    for c in review.get("exclude_countries", []):
        if "country" in df.columns:
            df = df[df["country"] != c]

    print(f"  ✅ {original_len} -> {len(df)} rows")
    return df


# ============================================================================
# AGENT 4: STATISTICS ENGINE (Code)
# ============================================================================
class StatisticsEngine:
    def run_all(self, df: pd.DataFrame, plan: dict) -> dict:
        print("\n📈 AGENT 4: Running statistical analysis...")
        results = {}

        for col in ["x", "y"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["x", "y"])

        if len(df) < 10:
            return {"error": "Insufficient data (< 10 observations)"}

        results["ols"] = self._ols(df)

        control_cols = [c for c in df.columns if c.startswith("control_")]
        if control_cols:
            results["ols_controls"] = self._ols_controls(df, control_cols)

        if df["country"].nunique() > 5:
            results["fixed_effects"] = self._fixed_effects(df)

        results["correlation"] = self._correlation(df)

        results["descriptive"] = {
            "n_obs": len(df),
            "n_countries": int(df["country"].nunique()),
            "year_range": f"{int(df['year'].min())}-{int(df['year'].max())}",
            "x_mean": round(float(df["x"].mean()), 4),
            "x_std": round(float(df["x"].std()), 4),
            "y_mean": round(float(df["y"].mean()), 4),
            "y_std": round(float(df["y"].std()), 4),
        }
        return results

    def _ols(self, df):
        print("  📐 OLS regression...")
        try:
            X = sm.add_constant(df["x"])
            model = sm.OLS(df["y"], X).fit()
            r = {
                "coefficient": round(float(model.params.iloc[1]), 6),
                "intercept": round(float(model.params.iloc[0]), 6),
                "std_error": round(float(model.bse.iloc[1]), 6),
                "t_stat": round(float(model.tvalues.iloc[1]), 4),
                "p_value": round(float(model.pvalues.iloc[1]), 6),
                "r_squared": round(float(model.rsquared), 4),
                "adj_r_squared": round(float(model.rsquared_adj), 4),
                "n_obs": int(model.nobs),
                "f_stat": round(float(model.fvalue), 4),
                "significant": float(model.pvalues.iloc[1]) < 0.05,
            }
            sig = "***" if r["p_value"] < 0.001 else "**" if r["p_value"] < 0.01 else "*" if r["p_value"] < 0.05 else ""
            print(f"    -> B = {r['coefficient']} (p = {r['p_value']}) {sig}, R2 = {r['r_squared']}")
            return r
        except Exception as e:
            print(f"    ⚠️  OLS failed: {e}")
            return {"error": str(e)}

    def _ols_controls(self, df, control_cols):
        print(f"  📐 OLS with {len(control_cols)} controls...")
        try:
            df_clean = df.dropna(subset=["x", "y"] + control_cols)
            X = sm.add_constant(df_clean[["x"] + control_cols])
            model = sm.OLS(df_clean["y"], X).fit()
            r = {
                "coefficient": round(float(model.params["x"]), 6),
                "std_error": round(float(model.bse["x"]), 6),
                "p_value": round(float(model.pvalues["x"]), 6),
                "r_squared": round(float(model.rsquared), 4),
                "adj_r_squared": round(float(model.rsquared_adj), 4),
                "n_obs": int(model.nobs),
                "significant": float(model.pvalues["x"]) < 0.05,
                "controls_used": control_cols,
            }
            print(f"    -> B = {r['coefficient']} (p = {r['p_value']}), R2 = {r['r_squared']}")
            return r
        except Exception as e:
            print(f"    ⚠️  OLS+controls failed: {e}")
            return {"error": str(e)}

    def _fixed_effects(self, df):
        print("  📐 Country fixed effects...")
        try:
            df_fe = df.copy()
            for col in ["x", "y"]:
                df_fe[f"{col}_dm"] = df_fe[col] - df_fe.groupby("country")[col].transform("mean")
            X = sm.add_constant(df_fe["x_dm"])
            model = sm.OLS(df_fe["y_dm"], X).fit()
            r = {
                "coefficient": round(float(model.params.iloc[-1]), 6),
                "std_error": round(float(model.bse.iloc[-1]), 6),
                "p_value": round(float(model.pvalues.iloc[-1]), 6),
                "r_squared_within": round(float(model.rsquared), 4),
                "n_obs": int(model.nobs),
                "n_countries": int(df["country"].nunique()),
                "significant": float(model.pvalues.iloc[-1]) < 0.05,
            }
            print(f"    -> B(FE) = {r['coefficient']} (p = {r['p_value']}), R2w = {r['r_squared_within']}")
            return r
        except Exception as e:
            print(f"    ⚠️  FE failed: {e}")
            return {"error": str(e)}

    def _correlation(self, df):
        print("  📐 Correlation...")
        try:
            pr, pp = scipystats.pearsonr(df["x"], df["y"])
            sr, sp = scipystats.spearmanr(df["x"], df["y"])
            r = {
                "pearson_r": round(float(pr), 4), "pearson_p": round(float(pp), 6),
                "spearman_r": round(float(sr), 4), "spearman_p": round(float(sp), 6),
            }
            print(f"    -> Pearson r = {r['pearson_r']}, Spearman rho = {r['spearman_r']}")
            return r
        except Exception as e:
            print(f"    ⚠️  Correlation failed: {e}")
            return {"error": str(e)}


# ============================================================================
# AGENT 5: RESULTS INTERPRETER (AI)
# ============================================================================
def ai_interpret_results(results: dict, plan: dict) -> dict:
    print("\n⚖️ AGENT 5: AI interpreting results...")
    interpretation = ask_claude_json(
        system="""You are an econometrics expert. Given statistical results, provide an honest assessment.
If R2 is 0.04, say "very weak." Do NOT oversell.
Return JSON:
{
    "strength": "strong / moderate / weak / very weak / none",
    "direction": "positive / negative / unclear",
    "confidence": "high / moderate / low",
    "main_finding": "One sentence summary",
    "caveats": ["limitations"],
    "recommended_tone": "confident / cautious / very cautious / skeptical",
    "additional_tests_suggested": []
}""",
        user=f"Hypothesis: {plan['statement']}\n\nResults:\n{json.dumps(results, indent=2, default=str)}",
    )
    print(f"  -> {interpretation.get('strength', '?')} | {interpretation.get('recommended_tone', '?')}")
    print(f"  -> {interpretation.get('main_finding', 'N/A')}")
    return interpretation


# ============================================================================
# AGENT 6: PAPER WRITER (AI — improved with McCloskey rules)
# ============================================================================
WRITING_RULES = """WRITING STYLE (follow strictly):
- Never start with "This paper" or "This study". Hook the reader with the puzzle or finding.
- Use active verbs: "We estimate" not "estimation was performed". Find the action, express it as a verb.
- Be concrete: "a $429 increase" not "a statistically significant positive association".
- No boilerplate: skip "the rest of this paper is organized as follows" or table-of-contents paragraphs.
- No elegant variation: if you call it "electricity access" once, don't switch to "electrification rate" then "energy provision" then "power availability". Pick one term and stick with it.
- "Significant" means statistically significant ONLY. For importance use "large", "substantial", "meaningful".
- Keep causality language honest: if the design only shows correlation, use "is associated with", "suggests", never "causes" or "leads to".
- No em dashes. Use commas, semicolons, or separate sentences.
- No five-dollar words when plain ones work: "use" not "utilize", "start" not "commence", "show" not "demonstrate".
- Avoid "this", "these", "those" as much as possible. Use "the" or repeat the noun.
- Write as if explaining to a smart colleague over coffee, not performing for a tenure committee.
- Equations: write them out with words when possible. "GDP per capita = α + β × Electricity Access + ε"
- No markdown formatting whatsoever. No #, **, *, `, $$, LaTeX.
- Do NOT write a full paper. Write ONLY the section requested."""

class PaperWriter:
    def __init__(self, plan, results, interpretation, literature):
        self.plan = plan
        self.results = results
        self.interp = interpretation
        self.literature = literature
        self._build_citation_block()

    def _build_citation_block(self):
        if not self.literature:
            self.cites = "No verified citations available. Do not cite any sources."
            return
        lines = ["VERIFIED CITATIONS - you may ONLY cite these:"]
        for i, a in enumerate(self.literature[:15]):
            lines.append(f"  {i+1}. {a['authors_short']} ({a['year']}). \"{a['title']}\". {a['journal']}.")
        lines.append("\nCRITICAL: Do NOT cite any source not listed above. No Becker, no Lucas, no Acemoglu unless listed.")
        self.cites = "\n".join(lines)

    def _verify_citations(self, text):
        valid = set()
        for a in self.literature:
            y = a.get("year", "")
            for auth in a.get("authors", []):
                ln = auth.split()[-1] if auth else ""
                if ln and y:
                    valid.add((ln.lower(), y))
            short = a.get("authors_short", "")
            if short:
                fw = short.split()[0].rstrip(",")
                if fw and y:
                    valid.add((fw.lower(), y))

        removed = []
        def check(m):
            ct = m.group(1)
            ym = re.search(r"(\d{4})", ct)
            if not ym:
                return m.group(0)
            yr = ym.group(1)
            ap = ct[:ym.start()].strip().rstrip(",").strip()
            for w in re.findall(r"[A-Za-z]+", ap):
                if (w.lower(), yr) in valid:
                    return m.group(0)
            removed.append(ct)
            return ""

        cleaned = re.compile(r"\(([^)]+?,\s*\d{4}[a-z]?)\)").sub(check, text)
        for r in removed:
            print(f"    ⚠️  Removed hallucinated citation: ({r})")
        return cleaned

    def write_all(self):
        print("\n📝 AGENT 6: Writing paper sections...")
        sections = {}
        for name, (sys_p, usr_p) in self._prompts().items():
            print(f"  📝 Writing: {name}...")
            raw = ask_claude(sys_p, usr_p, 3000)
            text = strip_markdown(raw)
            text = self._verify_citations(text)
            text = strip_duplicate_heading(text, name.replace("_", " "))
            sections[name] = text
            time.sleep(1)
        return sections

    def _prompts(self):
        desc = self.results.get("descriptive", {})
        ols_c = self.results.get("ols_controls", {})
        fe = self.results.get("fixed_effects", {})
        corr = self.results.get("correlation", {})

        # Prefer controlled results for prompts
        main_result = ols_c if ols_c and "error" not in ols_c else self.results.get("ols", {})
        fe_result = fe if fe and "error" not in fe else {}

        return {
            "abstract": (
                f"You are an economics journal writer. Write ONLY an abstract (150-200 words). {WRITING_RULES}\n{self.cites}",
                f"""Hypothesis: {self.plan['statement']}
X: {self.plan['x_label']}
Y: {self.plan['y_label']}
OLS+controls: B={main_result.get('coefficient','N/A')}, p={main_result.get('p_value','N/A')}, R2={main_result.get('r_squared','N/A')}
Fixed effects: B={fe_result.get('coefficient','N/A')}, p={fe_result.get('p_value','N/A')}, R2w={fe_result.get('r_squared_within','N/A')}
N={desc.get('n_obs','N/A')} observations, {desc.get('n_countries','N/A')} countries
Interpretation: {self.interp.get('main_finding','N/A')}
Tone: {self.interp.get('recommended_tone','cautious')}

Write a concise abstract. Focus on the controlled and fixed-effects results, not bivariate OLS. Start with the finding or puzzle, not "This paper examines".""",
            ),
            "introduction": (
                f"You are an economics journal writer. Write ONLY an introduction (400-500 words). {WRITING_RULES}\n{self.cites}",
                f"""Hypothesis: {self.plan['statement']}
X: {self.plan['x_label']}, Y: {self.plan['y_label']}
Main finding: {self.interp.get('main_finding','N/A')}
Tone: {self.interp.get('recommended_tone','cautious')}
Data: {desc.get('n_countries','N/A')} countries, {desc.get('year_range','N/A')}

Write the introduction. Hook the reader with a concrete fact or puzzle. Explain why the question matters using real-world stakes. Briefly preview the approach and finding. Do NOT include a roadmap paragraph ("Section 2 reviews...").""",
            ),
            "literature_review": (
                f"You are an economics journal writer. Write ONLY a literature review (400-600 words). {WRITING_RULES}\n{self.cites}\n\nCRITICAL: Only cite papers from the verified list. Organize by THEMES and DISAGREEMENTS, not paper-by-paper summaries. Identify 2-3 perspectives or tensions in the literature.",
                f"""Hypothesis: {self.plan['statement']}

Write the literature review. Do NOT summarize each paper sequentially. Instead:
1. Identify the main debate or tension in the literature
2. Group papers by what position they support
3. Note where evidence conflicts or where gaps exist
4. Connect to how your analysis addresses these gaps

Avoid starting every paragraph with an author name. Lead with the idea, then cite.""",
            ),
            "methodology_results": (
                f"You are an economics journal writer. Write ONLY methodology and results (600-800 words). {WRITING_RULES}",
                f"""Hypothesis: {self.plan['statement']}
X: {self.plan['x_label']} ({self.plan['independent_var']})
Y: {self.plan['y_label']} ({self.plan['dependent_var']})
Controls: {', '.join(c['label'] for c in self.plan.get('control_vars', []))}
Source: World Bank World Development Indicators

RESULTS (focus on controlled and fixed-effects, not bivariate OLS):
{json.dumps(self.results, indent=2, default=str)}

STRUCTURE:
Methodology section:
- State the equation clearly using words: "{self.plan['y_label']} = α + β × {self.plan['x_label']} + Controls + ε"
- Briefly mention the control variables and why they are included (1-2 sentences, not a paragraph per control)
- Describe the fixed effects specification
- Data source and coverage

Results section:
- Lead with the OLS+controls result (the default specification). This is the main result.
- Then show how fixed effects changes the picture
- Mention correlation coefficients briefly
- DO NOT dwell on the bivariate OLS without controls. It is naive and only useful as a benchmark.
- If the coefficient sign flips or the magnitude changes dramatically across specifications, EXPLAIN WHY. This is the story.
- Report exact numbers: coefficient, standard error, p-value, R-squared, N
- Do not describe what control variables "capture" in the results section. The reader knows.""",
            ),
            "conclusion": (
                f"You are an economics journal writer. Write ONLY a conclusion (250-400 words). {WRITING_RULES}\n{self.cites}",
                f"""Hypothesis: {self.plan['statement']}
Interpretation: {json.dumps(self.interp, indent=2, default=str)}
Main result (OLS+controls): B={main_result.get('coefficient','N/A')}, p={main_result.get('p_value','N/A')}
Fixed effects: B={fe_result.get('coefficient','N/A')}, p={fe_result.get('p_value','N/A')}

Write the conclusion. Be honest. If evidence is weak, say so directly.
- State what the analysis found (1-2 sentences)
- Acknowledge limitations concretely (endogeneity, omitted variables, measurement)
- Suggest what future work could do differently (specific methods, not vague "more research needed")
- End with a concrete policy implication or takeaway, appropriately hedged""",
            ),
        }


# ============================================================================
# AGENT 6b: PROOFREADER (AI — applies McCloskey rules)
# ============================================================================
def ai_proofread(sections: dict) -> dict:
    print("\n🔎 AGENT 6b: Proofreading all sections...")

    full_text = "\n\n---\n\n".join(
        f"[{name.upper()}]\n{text}" for name, text in sections.items() if text
    )

    proofread_text = ask_claude(
        system=f"""You are a meticulous academic editor trained in Deirdre McCloskey's writing rules. Your job is to proofread and improve economics papers.

{WRITING_RULES}

ADDITIONAL PROOFREADING RULES:
- Remove any sentence that begins with "This paper" or "This study" and rewrite it.
- Remove any table-of-contents paragraph ("The rest of the paper is organized as follows").
- Remove any section heading that got duplicated at the start of the section text.
- Fix nominalization: "there is a need for reanalysis" -> "we must reanalyze".
- Remove "very", "absolutely", "purely" unless they carry real meaning.
- Replace "significant" with "large/substantial/meaningful" unless referring to statistical significance.
- Remove "it is important to note that" and similar throat-clearing.
- Keep the EXACT same structure: each section starts with [SECTION_NAME] on its own line.
- Do NOT add new facts, citations, or data. Only improve the writing.
- Do NOT add markdown formatting.
- Keep the substance identical. Only improve clarity, tone, and style.""",
        user=f"Proofread and improve the following paper sections. Return the FULL text with the same [SECTION_NAME] markers:\n\n{full_text}",
        max_tokens=6000,
    )

    proofread_text = strip_markdown(proofread_text)

    # Parse back into sections
    improved = {}
    for name in sections:
        marker = f"[{name.upper()}]"
        if marker in proofread_text:
            start = proofread_text.index(marker) + len(marker)
            # Find next marker or end
            next_start = len(proofread_text)
            for other_name in sections:
                other_marker = f"[{other_name.upper()}]"
                if other_marker in proofread_text and proofread_text.index(other_marker) > start:
                    next_start = min(next_start, proofread_text.index(other_marker))
            text = proofread_text[start:next_start].strip()
            text = text.lstrip("-").strip()
            if len(text) > 50:  # Only use if substantial
                improved[name] = text
                print(f"  ✅ Proofread: {name}")
            else:
                improved[name] = sections[name]
        else:
            improved[name] = sections[name]

    return improved


# ============================================================================
# AGENT 7: DOCUMENT ASSEMBLER (Code — with tables and charts)
# ============================================================================
class DocumentAssembler:
    def _add_table(self, doc, headers, rows, col_widths=None):
        """Add a formatted table to the document."""
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header row
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(h)
            run.font.size = Pt(9)
            run.font.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Light gray background
            shading = cell._element.get_or_add_tcPr()
            shading_elm = shading.makeelement(qn("w:shd"), {
                qn("w:val"): "clear",
                qn("w:color"): "auto",
                qn("w:fill"): "E8E8E8",
            })
            shading.append(shading_elm)

        # Data rows
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                cell = table.rows[ri + 1].cells[ci]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(str(val))
                run.font.size = Pt(9)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        if col_widths:
            for i, w in enumerate(col_widths):
                for row in table.rows:
                    row.cells[i].width = Inches(w)

        doc.add_paragraph("")  # spacing

    def _add_descriptive_table(self, doc, results):
        """Add Table 1: Descriptive Statistics."""
        desc = results.get("descriptive", {})
        if not desc:
            return

        doc.add_paragraph("")
        p = doc.add_paragraph()
        run = p.add_run("Table 1: Descriptive Statistics")
        run.font.bold = True
        run.font.size = Pt(10)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        headers = ["Variable", "N", "Mean", "Std. Dev.", "Min", "Max"]
        rows = []
        for var_key, label in [("x", "X"), ("y", "Y")]:
            s = desc.get(f"{var_key}_stats", {})
            if s:
                rows.append([
                    label,
                    str(desc.get("n_obs", "")),
                    f"{s.get('mean', 0):.3f}",
                    f"{s.get('std', 0):.3f}",
                    f"{s.get('min', 0):.3f}",
                    f"{s.get('max', 0):.3f}",
                ])

        if rows:
            self._add_table(doc, headers, rows, [1.2, 0.7, 1.0, 1.0, 1.0, 1.0])

    def _add_regression_table(self, doc, results, plan):
        """Add Table 2: Regression Results."""
        doc.add_paragraph("")
        p = doc.add_paragraph()
        run = p.add_run("Table 2: Regression Results")
        run.font.bold = True
        run.font.size = Pt(10)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        headers = ["", "OLS + Controls", "Fixed Effects"]
        rows = []

        ols_c = results.get("ols_controls", {})
        fe = results.get("fixed_effects", {})

        def fmt_coef(r, key="coefficient", se_key="std_error", p_key="p_value"):
            if not r or "error" in r:
                return ""
            c = r.get(key, 0)
            se = r.get(se_key, 0)
            p = r.get(p_key, 1)
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            return f"{c:.4f}{stars}\n({se:.4f})"

        x_label = plan.get("x_label", "X")
        if len(x_label) > 30:
            x_label = x_label[:30] + "..."

        rows.append([x_label, fmt_coef(ols_c), fmt_coef(fe)])
        rows.append(["R²", f"{ols_c.get('r_squared', '')}", f"{fe.get('r_squared_within', '')} (within)"])
        rows.append(["N", str(ols_c.get("n_obs", "")), str(fe.get("n_obs", ""))])
        rows.append(["Controls", "Yes", "Country FE"])

        self._add_table(doc, headers, rows, [1.8, 1.8, 1.8])

        # Significance note
        p = doc.add_paragraph()
        run = p.add_run("Notes: * p < 0.05, ** p < 0.01, *** p < 0.001. Standard errors in parentheses.")
        run.font.size = Pt(8)
        run.font.italic = True

    def create(self, plan, sections, all_results, literature, controls_fetched, output_path,
               scatterplot_path=None, coeff_plot_path=None):
        print("\n📄 AGENT 7: Assembling document...")

        title = plan.get("title", "").strip()
        if not title:
            title = f"The Effect of {plan['x_label']} on {plan['y_label']}: A Cross-Country Panel Analysis"

        doc = Document()

        # Set default font
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)

        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title)
        run.font.size = Pt(16)
        run.font.bold = True

        # Date
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Generated by Empirica | {datetime.now().strftime('%B %d, %Y')}")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(128, 128, 128)

        doc.add_paragraph("")

        # Sections
        headings = {
            "abstract": "Abstract",
            "introduction": "1. Introduction",
            "literature_review": "2. Literature Review",
            "methodology_results": "3. Methodology and Results",
            "conclusion": "4. Conclusion and Policy Implications",
        }

        for key, heading in headings.items():
            text = sections.get(key, "")
            if not text:
                continue
            h = doc.add_heading(heading, level=1)
            for run in h.runs:
                run.font.size = Pt(13)
                run.font.color.rgb = RGBColor(0, 0, 0)

            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    p = doc.add_paragraph(para)
                    p.style.font.size = Pt(11)

            # Insert descriptive stats table after methodology heading
            if key == "methodology_results":
                self._add_descriptive_table(doc, all_results)
                # Insert scatterplot
                if scatterplot_path and os.path.exists(scatterplot_path):
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(f"Figure 1: {plan['x_label']} vs {plan['y_label']} by Region (Country Averages)")
                    run.font.bold = True
                    run.font.size = Pt(10)
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(scatterplot_path, width=Inches(5.5))
                    doc.add_paragraph("")

                # Insert regression table
                self._add_regression_table(doc, all_results, plan)

                # Insert coefficient plot
                if coeff_plot_path and os.path.exists(coeff_plot_path):
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run("Figure 2: Coefficient Estimates Across Specifications (95% Confidence Intervals)")
                    run.font.bold = True
                    run.font.size = Pt(10)
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(coeff_plot_path, width=Inches(4.5))
                    doc.add_paragraph("")

        # References
        if literature:
            doc.add_heading("References", level=1)
            for art in literature:
                ref = f"{art['authors_short']} ({art['year']}). {art['title']}. {art['journal']}."
                if art.get("doi"):
                    ref += f" DOI: {art['doi']}"
                p = doc.add_paragraph(ref)
                p.style.font.size = Pt(10)
                p.paragraph_format.space_after = Pt(4)

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        doc.save(output_path)
        print(f"  ✅ Paper saved: {output_path}")


class ReproductionScriptGenerator:
    def generate(self, plan, review, results, output_path):
        print(f"  💻 Reproduction script: {output_path}")
        controls_code = ""
        for ctrl in plan.get("control_vars", []):
            controls_code += f'    "{ctrl["code"]}",  # {ctrl["label"]}\n'

        script = f'''#!/usr/bin/env python3
"""
Reproduction Script - Generated by Empirica
Hypothesis: {plan["statement"]}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Run: pip install pandas statsmodels scipy requests
     python reproduce.py
"""
import requests, pandas as pd, numpy as np
import statsmodels.api as sm, scipy.stats as stats

X_IND = "{plan["independent_var"]}"
Y_IND = "{plan["dependent_var"]}"
CONTROLS = [
{controls_code}]
START, END = {plan.get("start_year", 2000)}, {plan.get("end_year", 2023)}
WINSORIZE = {review.get("winsorize", False)}
WIN_PCT = {review.get("winsorize_percentile", 1)} / 100
MIN_OBS = {review.get("min_observations_per_country", 3)}

AGGREGATES = {{"WLD","HIC","LIC","LMC","MIC","UMC","LMY","HPC","EAS","ECS","LCN","MEA","NAC","SAS","SSF"}}

def fetch_wb(ind, s, e):
    rows, page = [], 1
    while True:
        r = requests.get(f"https://api.worldbank.org/v2/country/all/indicator/{{ind}}?date={{s}}:{{e}}&format=json&per_page=1000&page={{page}}", timeout=30).json()
        if len(r) < 2 or not r[1]: break
        for rec in r[1]:
            v = rec.get("value")
            if v is not None:
                cc = rec["country"]["id"]
                if cc not in AGGREGATES:
                    rows.append({{"country": rec["country"]["value"], "cc": cc, "year": int(rec["date"]), "value": float(v)}})
        if page >= r[0].get("pages", 1): break
        page += 1
    return pd.DataFrame(rows)

print("Fetching data...")
xd = fetch_wb(X_IND, START, END)
yd = fetch_wb(Y_IND, START, END)
df = xd.rename(columns={{"value":"x"}}).merge(yd.rename(columns={{"value":"y"}})[["country","year","y"]], on=["country","year"])

if WINSORIZE:
    for c in ["x","y"]:
        df[c] = df[c].clip(df[c].quantile(WIN_PCT), df[c].quantile(1-WIN_PCT))
counts = df.groupby("country").size()
df = df[df["country"].isin(counts[counts >= MIN_OBS].index)]
print(f"Data: {{len(df)}} obs, {{df['country'].nunique()}} countries")

X = sm.add_constant(df["x"])
m = sm.OLS(df["y"], X).fit()
print(f"OLS: coef={{m.params.iloc[1]:.6f}}, p={{m.pvalues.iloc[1]:.6f}}, R2={{m.rsquared:.4f}}")

dfe = df.copy()
for c in ["x","y"]: dfe[f"{{c}}_dm"] = dfe[c] - dfe.groupby("country")[c].transform("mean")
Xfe = sm.add_constant(dfe["x_dm"])
fem = sm.OLS(dfe["y_dm"], Xfe).fit()
print(f"FE:  coef={{fem.params.iloc[-1]:.6f}}, p={{fem.pvalues.iloc[-1]:.6f}}, R2w={{fem.rsquared:.4f}}")

pr,pp = stats.pearsonr(df["x"], df["y"])
sr,sp = stats.spearmanr(df["x"], df["y"])
print(f"Pearson: r={{pr:.4f}} (p={{pp:.6f}})")
print(f"Spearman: rho={{sr:.4f}} (p={{sp:.6f}})")
print("Done.")
'''
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(script)
        print(f"  ✅ Script saved: {output_path}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================
def run_empirica(hypothesis: str, output_dir: str = OUTPUT_DIR):
    print("\n" + "=" * 60)
    print("  EMPIRICA v4.3")
    print("=" * 60)
    print(f"  Input: {hypothesis}")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # Agent 1: Parse
    plan = ai_parse_hypothesis(hypothesis)

    # Agent 2a: Fetch data
    print("\n📊 AGENT 2a: Fetching World Bank data...")
    wb = WorldBankFetcher()
    x_data = wb.fetch(plan["independent_var"], plan["start_year"], plan["end_year"])
    y_data = wb.fetch(plan["dependent_var"], plan["start_year"], plan["end_year"])
    if x_data.empty or y_data.empty:
        raise ValueError("Could not fetch data from World Bank.")

    df = x_data.rename(columns={"value": "x"}).merge(
        y_data.rename(columns={"value": "y"})[["country", "year", "y"]],
        on=["country", "year"],
    )

    controls_fetched = []
    for ctrl in plan.get("control_vars", []):
        cd = wb.fetch(ctrl["code"], plan["start_year"], plan["end_year"])
        if not cd.empty:
            cn = f"control_{ctrl['code'].replace('.', '_')}"
            cd = cd.rename(columns={"value": cn})
            df = df.merge(cd[["country", "year", cn]], on=["country", "year"], how="left")
            controls_fetched.append(ctrl)

    print(f"\n  ✅ Merged: {len(df)} rows, {df['country'].nunique()} countries")

    # Agent 2b: Literature
    lit = LiteratureSearcher()
    literature = lit.search(
        plan.get("semantic_scholar_query", plan["statement"]),
        plan.get("pubmed_query", plan["statement"]),
    )

    # Agent 3: Review data
    review = ai_review_data(df, plan)
    df = apply_cleaning(df, review)
    if len(df) < 10:
        raise ValueError(f"Only {len(df)} observations after cleaning.")

    # Agent 4: Statistics
    engine = StatisticsEngine()
    results = engine.run_all(df, plan)
    if "error" in results:
        raise ValueError(f"Analysis failed: {results['error']}")

    # Generate charts
    scatterplot_path = ""
    coeff_plot_path = ""
    try:
        scatterplot_path = generate_scatterplot(df, plan, output_dir)
    except Exception as e:
        print(f"  ⚠️  Scatterplot failed: {e}")
    try:
        coeff_plot_path = generate_coefficient_plot(results, plan, output_dir)
    except Exception as e:
        print(f"  ⚠️  Coefficient plot failed: {e}")

    # Agent 5: Interpret
    interpretation = ai_interpret_results(results, plan)

    # Agent 6: Write
    writer = PaperWriter(plan, results, interpretation, literature)
    sections = writer.write_all()

    # Agent 6b: Proofread
    sections = ai_proofread(sections)

    # Agent 7: Assemble
    paper_path = os.path.join(output_dir, "paper.docx")
    assembler = DocumentAssembler()
    assembler.create(plan, sections, results, literature, controls_fetched, paper_path,
                     scatterplot_path=scatterplot_path, coeff_plot_path=coeff_plot_path)

    repro_path = os.path.join(output_dir, "reproduce.py")
    ReproductionScriptGenerator().generate(plan, review, results, repro_path)

    print("\n" + "=" * 60)
    print("  ✅ EMPIRICA v4.3 COMPLETE")
    print("=" * 60)
    print(f"  Paper:  {paper_path}")
    print(f"  Code:   {repro_path}")
    main_r = results.get("ols_controls", results.get("ols", {}))
    print(f"  Result: B={main_r.get('coefficient','N/A')}, p={main_r.get('p_value','N/A')}, R2={main_r.get('r_squared','N/A')}")
    print("=" * 60)

    return results


# ============================================================================
# CLI ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_empirica(" ".join(sys.argv[1:]))
    else:
        print("Usage: python empirica_v3.py \"Your hypothesis here\"")
        sys.exit(1)
