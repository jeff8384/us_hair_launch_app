"""Streamlit Cloud entry point for the US Hair Launch workflow.

Renders the committed pipeline outputs under data/processed and data/exports
so the analysis is browsable without the local FastAPI app or source files.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

st.set_page_config(page_title="US Hair Launch App", page_icon="💇", layout="wide")


@st.cache_data
def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def pattern_table(patterns: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(patterns).rename(columns={"pattern": "Pattern", "count": "Count"})


gaps = load_json(PROCESSED_DIR / "competitor_gaps.json")
claims = load_jsonl(PROCESSED_DIR / "competitor_claims.jsonl")
message_map = load_json(PROCESSED_DIR / "message_map_candidates.json")
pdp = load_json(PROCESSED_DIR / "pdp_blocks.json")

st.title("💇 US Hair Launch App")
st.caption("US hair-care competitor analysis and PDP copy workflow — pipeline outputs")

if not any([gaps, claims, message_map, pdp]):
    st.error(
        "No pipeline outputs found under `data/processed/`. "
        "Run the local pipeline and commit the results before deploying."
    )
    st.stop()

tab_gaps, tab_claims, tab_map, tab_pdp = st.tabs(
    ["📊 Gap Analysis", "🔎 Competitor Claims", "🗺️ Message Map", "📝 PDP Copy"]
)

with tab_gaps:
    if not gaps:
        st.info("`competitor_gaps.json` is missing.")
    else:
        st.subheader("Summary")
        st.write(gaps["summary"])

        cols = st.columns(1 + len(gaps["retailer_breakdown"]))
        cols[0].metric("Total records", gaps["total_records"])
        for col, retailer in zip(cols[1:], gaps["retailer_breakdown"]):
            col.metric(retailer["retailer"].title(), retailer["record_count"])

        left, right = st.columns(2)
        with left:
            st.subheader("Top claim patterns")
            st.dataframe(pattern_table(gaps["top_claim_patterns"]), hide_index=True)
        with right:
            st.subheader("Top proof patterns")
            st.dataframe(pattern_table(gaps["top_proof_patterns"]), hide_index=True)

        st.subheader("Category insights")
        for item in gaps["category_insights"]:
            st.markdown(f"- {item}")

        st.subheader("Gap opportunities")
        for item in gaps["gap_opportunities"]:
            st.markdown(f"- {item}")

        st.subheader("Retailer differences")
        for item in gaps["retailer_specific_differences"]:
            st.markdown(f"- {item}")

        for retailer in gaps["retailer_breakdown"]:
            with st.expander(f"Retailer detail — {retailer['retailer']}"):
                st.dataframe(pattern_table(retailer["top_claim_patterns"]), hide_index=True)
                for item in retailer.get("whitespace", []):
                    st.markdown(f"- {item}")

with tab_claims:
    if not claims:
        st.info("`competitor_claims.jsonl` is missing.")
    else:
        df = pd.DataFrame(claims)

        filter_cols = st.columns(3)
        retailers = filter_cols[0].multiselect(
            "Retailer", sorted(df["retailer"].unique()), placeholder="All retailers"
        )
        concerns = sorted({c for row in df["target_concerns"] for c in row})
        selected_concerns = filter_cols[1].multiselect(
            "Target concern", concerns, placeholder="All concerns"
        )
        brand_query = filter_cols[2].text_input("Brand / product search")

        filtered = df
        if retailers:
            filtered = filtered[filtered["retailer"].isin(retailers)]
        if selected_concerns:
            filtered = filtered[
                filtered["target_concerns"].apply(
                    lambda row: any(c in row for c in selected_concerns)
                )
            ]
        if brand_query:
            query = brand_query.lower()
            filtered = filtered[
                filtered["brand"].str.lower().str.contains(query, regex=False)
                | filtered["product_name"].str.lower().str.contains(query, regex=False)
            ]

        st.caption(f"{len(filtered)} of {len(df)} records")
        st.dataframe(
            filtered[
                [
                    "retailer",
                    "brand",
                    "product_name",
                    "hero_claim",
                    "proof_type",
                    "ingredients_called_out",
                    "target_concerns",
                    "compliance_risk",
                ]
            ],
            hide_index=True,
            height=560,
        )

with tab_map:
    if not message_map:
        st.info("`message_map_candidates.json` is missing.")
    else:
        st.caption(message_map.get("source_summary", ""))
        for territory in message_map["territories"]:
            st.subheader(territory["territory"])
            st.markdown(f"**Core promise:** {territory['core_promise']}")
            st.markdown(f"**Differentiator:** {territory['differentiator']}")
            st.markdown(f"**Proof direction:** {territory['proof_direction']}")
            st.markdown(f"**Emotional payoff:** {territory['emotional_payoff']}")

            left, right = st.columns(2)
            with left:
                st.markdown("**Headline options**")
                for line in territory["headline_options"]:
                    st.markdown(f"- {line}")
                st.markdown("**Subheadline options**")
                for line in territory["subheadline_options"]:
                    st.markdown(f"- {line}")
            with right:
                st.markdown("**Benefit bullets**")
                for line in territory["benefit_bullets"]:
                    st.markdown(f"- {line}")
                st.markdown("**Compliance-safe rewrites**")
                for line in territory["compliance_safe_rewrites"]:
                    st.markdown(f"- {line}")

            st.markdown(f"*Recommended use case:* {territory['recommended_use_case']}")
            st.divider()

with tab_pdp:
    if not pdp:
        st.info("`pdp_blocks.json` is missing.")
    else:
        copy_modes = pdp.get("copy_modes", {})
        mode = st.radio("Copy mode", list(copy_modes) or ["blocks"], horizontal=True)

        blocks = copy_modes.get(mode, {})
        for name, block in blocks.items():
            with st.container(border=True):
                st.markdown(f"##### {name.replace('_', ' ').title()}")
                if block.get("headline"):
                    st.markdown(f"**{block['headline']}**")
                if block.get("body"):
                    st.write(block["body"])
                for bullet in block.get("bullets", []):
                    st.markdown(f"- {bullet}")
                if block.get("cta"):
                    st.markdown(f"CTA: `{block['cta']}`")

        if pdp.get("faq"):
            st.subheader("FAQ")
            for item in pdp["faq"]:
                with st.expander(item["question"]):
                    st.write(item["answer"])

        drafts_path = EXPORTS_DIR / "pdp_copy_drafts.md"
        if drafts_path.exists():
            st.download_button(
                "Download PDP copy drafts (Markdown)",
                data=drafts_path.read_text(encoding="utf-8"),
                file_name="pdp_copy_drafts.md",
                mime="text/markdown",
            )
