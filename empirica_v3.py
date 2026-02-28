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
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

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


# ============================================================================
# TAUTOLOGY GUARD (v4.1)
# ============================================================================
def check_tautology(x_code: str, y_code: str) -> bool:
    for prefix in INDICATOR_FAMILIES:
        if x_code.startswith(prefix) and y_code.startswith(prefix):
            return True
    return x_code == y_code


# ============================================================================
# AGENT 1: HYPOTHESIS PARSER (AI)
# ============================================================================
def ai_parse_hypothesis(hypothesis_text: str) -> dict:
    print("\n🧠 AGENT 1: Parsing hypothesis with AI...")

    plan = ask_claude_json(
        system="""You are a research methodology expert. Given a hypothesis, pick World Bank indicators.

CRITICAL RULES:
1. X and Y MUST be from DIFFERENT domains (e.g., health spending -> life expectancy, NOT GDP growth -> GDP per capita growth)
2. NEVER pick two GDP indicators, two health indicators, or two education indicators as X and Y
3. The relationship must be CAUSAL/INTERESTING, not an accounting identity
4. Pick 2-4 control variables that are CONFOUNDERS (affect both X and Y)

World Bank indicators:
ECONOMIC:
- NY.GDP.PCAP.PP.KD = GDP per capita (PPP, constant 2017 $)
- NY.GDP.PCAP.KD.ZG = GDP per capita growth (annual %)
- FP.CPI.TOTL.ZG = Inflation (annual %)
- SL.UEM.TOTL.ZS = Unemployment (%)

EDUCATION:
- SE.XPD.TOTL.GD.ZS = Education expenditure (% of GDP)
- SE.SEC.ENRR = Secondary school enrollment (% gross)
- SE.TER.ENRR = Tertiary enrollment (% gross)

HEALTH:
- SH.XPD.CHEX.GD.ZS = Health expenditure (% of GDP)
- SP.DYN.LE00.IN = Life expectancy (years)
- SP.DYN.IMRT.IN = Infant mortality rate (per 1,000)
- SH.MED.PHYS.ZS = Physicians (per 1,000 people)

INFRASTRUCTURE & GOVERNANCE:
- IT.NET.USER.ZS = Internet users (% of population)
- EG.ELC.ACCS.ZS = Access to electricity (%)
- SP.URB.TOTL.IN.ZS = Urban population (%)
- GE.EST = Government effectiveness

INEQUALITY:
- SI.POV.GINI = Gini index
- SP.POP.GROW = Population growth (%)

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
    "reasoning": "explanation"
}

EXAMPLE for "healthcare spending -> life expectancy":
- independent_var: "SH.XPD.CHEX.GD.ZS" (health expenditure % GDP)
- dependent_var: "SP.DYN.LE00.IN" (life expectancy)
- controls: GDP per capita, education enrollment, urbanization""",
        user=f'Hypothesis: "{hypothesis_text}"\n\nPick the CORRECT X and Y indicators. X must be the CAUSE, Y must be the EFFECT.',
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
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"    ⚠️  World Bank API error: {e}")
                break

            if len(data) < 2 or not data[1]:
                break

            for record in data[1]:
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

            if page >= data[0].get("pages", 1):
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
# AGENT 6: PAPER WRITER (AI x5 calls)
# ============================================================================
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
        lines.append("\nDo NOT cite any source not listed above.")
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

    def _rules(self):
        return "RULES: Write ONLY the requested section. No markdown. No full paper. Clean academic prose."

    def write_all(self):
        print("\n📝 AGENT 6: Writing paper sections...")
        sections = {}
        for name, (sys_p, usr_p) in self._prompts().items():
            print(f"  📝 Writing: {name}...")
            raw = ask_claude(sys_p, usr_p, 3000)
            text = strip_markdown(raw)
            text = self._verify_citations(text)
            sections[name] = text
            time.sleep(1)
        return sections

    def _prompts(self):
        desc = self.results.get("descriptive", {})
        ols = self.results.get("ols", {})
        return {
            "abstract": (
                f"You are an academic writer. Write ONLY an abstract (150-250 words).\n{self._rules()}\n{self.cites}",
                f"Hypothesis: {self.plan['statement']}\nFinding: {self.interp.get('main_finding','N/A')}\nStrength: {self.interp.get('strength','N/A')}\nOLS: B={ols.get('coefficient','N/A')}, p={ols.get('p_value','N/A')}, R2={ols.get('r_squared','N/A')}\nN={desc.get('n_obs','N/A')} obs, {desc.get('n_countries','N/A')} countries\nWrite the abstract.",
            ),
            "introduction": (
                f"You are an academic writer. Write ONLY an introduction (400-600 words).\n{self._rules()}\n{self.cites}",
                f"Hypothesis: {self.plan['statement']}\nX: {self.plan['x_label']}\nY: {self.plan['y_label']}\nTone: {self.interp.get('recommended_tone','cautious')}\nData: {desc.get('n_countries','N/A')} countries, {desc.get('year_range','N/A')}\nWrite the introduction.",
            ),
            "literature_review": (
                f"You are an academic writer. Write ONLY a literature review (400-700 words).\n{self._rules()}\n{self.cites}\nCRITICAL: Only cite papers from the verified list.",
                f"Hypothesis: {self.plan['statement']}\nWrite the literature review using ONLY verified citations.",
            ),
            "methodology_results": (
                f"You are an academic writer. Write ONLY methodology + results (600-1000 words).\n{self._rules()}\nPresent all coefficients, p-values, R2, sample sizes.",
                f"Hypothesis: {self.plan['statement']}\nX: {self.plan['x_label']} ({self.plan['independent_var']})\nY: {self.plan['y_label']} ({self.plan['dependent_var']})\nData: World Bank\n{json.dumps(self.results, indent=2, default=str)}\nWrite methodology and results.",
            ),
            "conclusion": (
                f"You are an academic writer. Write ONLY a conclusion (300-500 words).\n{self._rules()}\n{self.cites}\nMatch tone to evidence strength.",
                f"Hypothesis: {self.plan['statement']}\nInterpretation: {json.dumps(self.interp, indent=2, default=str)}\nOLS: B={ols.get('coefficient','N/A')}, p={ols.get('p_value','N/A')}\nWrite the conclusion. Be honest about limitations.",
            ),
        }


# ============================================================================
# AGENT 7: DOCUMENT ASSEMBLER (Code)
# ============================================================================
class DocumentAssembler:
    def create(self, plan, sections, all_results, literature, controls_fetched, output_path):
        print("\n📄 AGENT 7: Assembling document...")

        title = plan.get("title", "").strip()
        if not title:
            title = f"The Effect of {plan['x_label']} on {plan['y_label']}: A Cross-Country Panel Analysis"

        doc = Document()

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
            "conclusion": "4. Conclusion",
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
    print("  EMPIRICA v4.1")
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

    # Agent 5: Interpret
    interpretation = ai_interpret_results(results, plan)

    # Agent 6: Write
    writer = PaperWriter(plan, results, interpretation, literature)
    sections = writer.write_all()

    # Agent 7: Assemble
    paper_path = os.path.join(output_dir, "paper.docx")
    assembler = DocumentAssembler()
    assembler.create(plan, sections, results, literature, controls_fetched, paper_path)

    repro_path = os.path.join(output_dir, "reproduce.py")
    ReproductionScriptGenerator().generate(plan, review, results, repro_path)

    print("\n" + "=" * 60)
    print("  ✅ EMPIRICA COMPLETE")
    print("=" * 60)
    print(f"  Paper:  {paper_path}")
    print(f"  Code:   {repro_path}")
    ols = results.get("ols", {})
    print(f"  Result: B={ols.get('coefficient','N/A')}, p={ols.get('p_value','N/A')}, R2={ols.get('r_squared','N/A')}")
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
