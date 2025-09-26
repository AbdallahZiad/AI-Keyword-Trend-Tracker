import pandas as pd
import streamlit as st
import json
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports from core
from core.keyword_expander import expand_keywords_batch
from core.data_provider.google_ads_provider import GoogleAdsProvider
from core.trend_analyzer import TrendAnalyzer
from core.ai_website_keyword_scanner import scan_website_for_keywords
from database.db_client import DBClient
from core.keyword_idea_expander import KeywordIdeaExpander
from core.data_provider.google_ads_mappings import GEO_TARGET_MAP, LANGUAGE_MAP


# --- Functions for UI state management ---
def _add_category():
    if "structured_input" not in st.session_state:
        st.session_state.structured_input = []
    st.session_state.structured_input.append({
        "category_name": f"New Category {len(st.session_state.structured_input) + 1}",
        "category_id": None,
        "ad_groups": []
    })
    st.session_state.last_action = "add_category"


def _remove_category(category_name):
    st.session_state.structured_input = [category for category in st.session_state.structured_input if category['category_name'] != category_name]
    st.session_state.last_action = "remove_category"


def _add_ad_group(category_index: int):
    if "structured_input" not in st.session_state:
        st.session_state.structured_input = []
    if category_index >= len(st.session_state.structured_input):
        return
    category = st.session_state.structured_input[category_index]
    category["ad_groups"].append({
        "ad_group_name": f"New Ad Group {len(category['ad_groups']) + 1}",
        "ad_group_id": None,
        "keywords": ""
    })
    st.session_state.last_action = "add_ad_group"


def _remove_ad_group(category_index: int, ad_group_index: int):
    st.session_state.structured_input[category_index]["ad_groups"].pop(ad_group_index)
    st.session_state.last_action = "remove_ad_group"


def _update_category_name(index: int):
    if f'category_name_input_{index}' in st.session_state:
        st.session_state.structured_input[index]["category_name"] = st.session_state[f'category_name_input_{index}']


def _update_ad_group_name(cat_idx: int, ag_idx: int):
    if f'ad_group_name_input_{cat_idx}_{ag_idx}' in st.session_state:
        st.session_state.structured_input[cat_idx]["ad_groups"][ag_idx]["ad_group_name"] = st.session_state[
            f'ad_group_name_input_{cat_idx}_{ag_idx}']


def _update_keywords(cat_idx: int, ag_idx: int):
    if f'keywords_text_area_{cat_idx}_{ag_idx}' in st.session_state:
        st.session_state.structured_input[cat_idx]["ad_groups"][ag_idx]["keywords"] = st.session_state[
            f'keywords_text_area_{cat_idx}_{ag_idx}']


def _load_db_data_to_state():
    """Fetches all categories, ad groups, and keywords from the database and loads them into session state."""
    with DBClient() as db:
        db_categories = db.get_all_categories()
        structured_data = []
        for cat in db_categories:
            category_entry = {
                "category_id": cat["id"],
                "category_name": cat["name"],
                "ad_groups": []
            }
            db_ad_groups = db.get_ad_groups_by_category(cat["id"])

            db_keywords = db.get_keywords_by_category(cat["id"])
            keywords_by_ad_group = {}
            for kw in db_keywords:
                ad_group_name = kw['ad_group_name']
                if ad_group_name not in keywords_by_ad_group:
                    keywords_by_ad_group[ad_group_name] = []
                keywords_by_ad_group[ad_group_name].append(kw['keyword'])

            for ag in db_ad_groups:
                ad_group_entry = {
                    "ad_group_id": ag["id"],
                    "ad_group_name": ag["name"],
                    "keywords": "\n".join(keywords_by_ad_group.get(ag['name'], []))
                }
                category_entry["ad_groups"].append(ad_group_entry)

            structured_data.append(category_entry)

        st.session_state.structured_input = structured_data
        st.session_state.original_db_state = structured_data.copy()


def _autosave_state_to_db():
    """Saves the current session state to the database."""
    with DBClient() as db:
        try:
            db.clear_all_data()

            for category in st.session_state.structured_input:
                category_id = db.upsert_category(category['category_name'])
                if not category_id:
                    raise ValueError(f"Failed to upsert category: {category['category_name']}")

                for ad_group in category['ad_groups']:
                    ad_group_id = db.upsert_ad_group(ad_group['ad_group_name'], category_id)
                    if not ad_group_id:
                        raise ValueError(f"Failed to upsert ad group: {ad_group['ad_group_name']}")

                    try:
                        keywords = ad_group['keywords'].strip().split('\n')
                    except Exception as e:
                        pass

                    for keyword in keywords:
                        if keyword:
                            db.upsert_keyword(keyword.strip(), ad_group_id)

            db.conn.commit()
            st.toast("✅ Changes saved to database!")

        except Exception as e:
            st.error(f"❌ Could not save changes. Data has been rolled back: {e}")
            raise


def _perform_enrichment():
    """Performs the keyword enrichment using the expander."""
    try:
        expander_data = []
        for category in st.session_state.structured_input:
            new_category = {
                "category": category["category_name"],
                "ad_groups": []
            }
            for ad_group in category["ad_groups"]:
                # Ensure all ad groups are processed, including those with no keywords
                keywords_list = [{"keyword": kw.strip()} for kw in ad_group["keywords"].strip().split('\n') if
                                 kw.strip()]
                new_ad_group = {
                    "ad_group": ad_group["ad_group_name"],
                    "keywords": keywords_list
                }
                new_category["ad_groups"].append(new_ad_group)
            expander_data.append(new_category)

        # The expander now receives the full data structure and handles the logic
        # of which ad groups need enrichment.
        provider = GoogleAdsProvider(data=[])
        expander = KeywordIdeaExpander(google_ads_provider=provider)
        expanded_data = expander.expand_keywords(expander_data)

        # Update the session state with the new keywords
        for i, category in enumerate(expanded_data):
            for j, ad_group in enumerate(category.get("ad_groups", [])):
                keywords_list = [kw.get('keyword', '') for kw in ad_group.get('keywords', [])]
                # Join the keywords with newlines and update the session state
                st.session_state.structured_input[i]["ad_groups"][j]["keywords"] = "\n".join(keywords_list)

    except Exception as e:
        st.error(f"❌ An error occurred during enrichment: {e}")


def _run_enrichment():
    """Triggers the enrichment process by first saving changes, then setting a flag."""
    if "structured_input" not in st.session_state or not st.session_state.structured_input:
        st.warning("No data to enrich. Please add categories and ad groups first.")
        return

    _autosave_state_to_db()
    st.session_state.enrichment_triggered = True
    st.toast("Enrichment started...", icon="⏳")
    st.rerun()


def _perform_analysis(country: str, language: str):
    """Performs the full analysis pipeline."""
    try:
        provider_data = []
        for category in st.session_state.structured_input:
            new_category = {
                "category": category["category_name"],
                "ad_groups": []
            }
            for ad_group in category["ad_groups"]:
                keywords_list = [{"keyword": kw.strip()} for kw in ad_group["keywords"].strip().split('\n') if
                                 kw.strip()]
                new_ad_group = {
                    "ad_group": ad_group["ad_group_name"],
                    "keywords": keywords_list
                }
                new_category["ad_groups"].append(new_ad_group)
            provider_data.append(new_category)

        # Use the passed country and language parameters
        provider = GoogleAdsProvider(
            data=provider_data,
            geo_target_id=GEO_TARGET_MAP[country],
            language_code=LANGUAGE_MAP[language],
        )
        augmented_data = provider.generate_output()

        analyzer = TrendAnalyzer()
        analyzed_results = analyzer.analyze(augmented_data)

        print("\n" + "=" * 50)
        print("Data with Historical Search Volumes:")
        print("=" * 50)
        print(json.dumps(augmented_data, indent=2))
        print("=" * 50 + "\n")

        print("\n" + "=" * 50)
        print("Trend Analysis Results:")
        print("=" * 50)
        print(json.dumps(analyzed_results, indent=2))
        print("=" * 50 + "\n")

        # Store the results in session state for the UI to access
        st.session_state.analysis_results = analyzed_results

        st.success("✅ Analysis complete! Check the console for historical data and trend forecasts.")

    except Exception as e:
        st.error(f"❌ An error occurred during analysis: {e}")


def _run_analysis_pipeline():
    """Triggers the analysis process by first saving changes, then setting a flag."""
    if "structured_input" not in st.session_state or not st.session_state.structured_input:
        st.warning("No data to analyze. Please add categories and ad groups first.")
        return

    _autosave_state_to_db()
    st.session_state.analysis_triggered = True
    st.toast("Running analysis...", icon="⏳")
    st.rerun()


def _save_changes():
    """Triggers the save process by setting a flag."""
    if "structured_input" not in st.session_state or not st.session_state.structured_input:
        st.warning("No data to save. Please add categories and ad groups first.")
        return

    st.session_state.save_triggered = True
    st.toast("Saving changes...", icon="💾")
    st.rerun()


# --- Utility functions for rendering ---
def _format_percentage(value: float) -> str:
    """Formats a float as a percentage with two decimal places and a sign."""
    if pd.isna(value):
        return "N/A"
    formatted_value = f"{value:.2f}%"
    if value > 0:
        return f"+{formatted_value}"
    return formatted_value


def _format_volatility_score(value: float) -> str:
    """Formats a volatility score with two decimal places."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


@st.cache_data(show_spinner=False)
def run_website_scan_cached(start_url: str, existing_structure, depth: int, max_pages: int, max_keywords: int):
    """
    Runs the website keyword scan with caching to prevent re-running on every change.
    """
    return scan_website_for_keywords(start_url.strip(), existing_structure, depth, max_pages, max_keywords)