import logging

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import json
import plotly.express as px
from ui_helpers import display_header, display_section_title
from typing import List, Dict, Any
from datetime import datetime

# Add the project root to sys.path for imports from core and database
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all utility functions from the new file
from dashboard.app_utils import (
    _add_category,
    _remove_category,
    _add_ad_group,
    _remove_ad_group,
    _update_category_name,
    _update_ad_group_name,
    _update_keywords,
    _load_db_data_to_state,
    _autosave_state_to_db,
    _perform_enrichment,
    _run_enrichment,
    _perform_analysis,
    _run_analysis_pipeline,
    _save_changes,
    _format_volatility_score,
    _format_percentage,
    run_website_scan_cached
)

# Import the correct mappings for country and language
from core.data_provider.google_ads_mappings import GEO_TARGET_MAP, LANGUAGE_MAP

# --- Streamlit Page Configuration & CSS ---
st.set_page_config(
    layout="wide",
    page_title="Keyword Dashboard",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    body { background-color: #F0F2F6 !important; color: #333333 !important; }
    .stApp > div:first-child > section.main {
        background-color: white !important; padding: 35px !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06) !important; margin: 25px auto !important;
        max-width: 900px !important; width: 95% !important;
    }
    .block-container { padding-top: 1rem !important; padding-right: 2.5rem !important; padding-left: 2.5rem !important; padding-bottom: 1.5rem !important; }
    h1 { font-size: 2.2em !important; margin-bottom: 0.8rem !important; color: #222222 !important; font-weight: 700 !important; }
    h2 { font-size: 1.3em !important; margin-top: 2.8rem !important; margin-bottom: 0.9rem !important; color: #333333 !important; font-weight: 600 !important; }
    h3 { font-size: 1.0em !important; color: #555555 !important; margin-bottom: 0.5rem !important; font-weight: 500 !important; }
    p, label, .stMarkdown, .stNumberInput, .stTextInput { font-family: 'Segoe UI', Arial, sans-serif !important; color: #555555 !important; line-height: 1.5 !important; }
    .page-divider { border-bottom: 1px solid #D5D5D5 !important; margin-bottom: 2rem; width: 100%; }
    div[data-testid="stMarkdownContainer"] table {
        width: 100% !important; border-collapse: separate !important; border-spacing: 0 !important;
        border: 1px solid #E0E0E0 !important; border-radius: 6px !important;
        margin-top: 1.5rem !important; margin-bottom: 3.0rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    }
    .table-responsive-wrapper {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    div[data-testid="stMarkdownContainer"] th {
        background-color: #E6EBF2 !important; color: #333333 !important; font-weight: 600 !important;
        text-align: left !important; padding: 14px 20px !important; border-bottom: 1px solid #C9D0DA !important;
        border-right: 1px solid #D5D5D5 !important; font-size: 0.85em !important; text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }
    div[data-testid="stMarkdownContainer"] th:last-child { border-right: none !important; }
    div[data-testid="stMarkdownContainer"] td {
        padding: 12px 20px !important; border-bottom: 1px solid #F0F0F0 !important;
        border-right: 1px solid #F0F0F0 !important; vertical-align: middle !important;
        font-size: 0.98em !important; color: #333333 !important;
    }
    div[data-testid="stMarkdownContainer"] td:last-child { border-right: none !important; }
    div[data-testid="stMarkdownContainer"] tr:last-child td { border-bottom: none !important; }
    div[data-testid="stMarkdownContainer"] tr:hover { background-color: #FAFAFA !important; }
    div[data-testid="stMarkdownContainer"] th:first-child, div[data-testid="stMarkdownContainer"] td:first-child { text-align: center !important; width: 1% !important; padding: 14px 10px !important; }
    div[data-testid="stMarkdownContainer"] th:nth-child(3), div[data-testid="stMarkdownContainer"] td:nth-child(3),
    div[data-testid="stMarkdownContainer"] th:nth-child(4), div[data-testid="stMarkdownContainer"] td:nth-child(4),
    div[data-testid="stMarkdownContainer"] th:nth-child(5), div[data-testid="stMarkdownContainer"] td:nth-child(5) { text-align: right !important; }
    div[data-testid="stMarkdownContainer"] th:last-child, div[data-testid="stMarkdownContainer"] td:last-child { text-align: center !important; padding-right: 20px !important; }
    div[data-testid="stMarkdownContainer"] span { font-weight: 600 !important; }
    span[style*="color:green"] { color: #28a745 !important; }
    span[style*="color:red"] { color: #dc3545 !important; }
    div[data-testid="stMarkdownContainer"] td span { font-size: 1.15em !important; line-height: 1 !important; display: inline-block; vertical-align: middle; }

    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {
        background-color: white !important; border: 1px solid #D5D5D5 !important; border-radius: 5px !important;
        box-shadow: none !important; padding: 10px 14px !important; color: #333333 !important;
        font-size: 0.95em !important; outline: none !important;
        height: 38px !important;
    }
    div[data-testid="stNumberInput"] input:focus, div[data-testid="stTextInput"] input:focus {
        border-color: #9ECFFB !important; box-shadow: 0 0 0 2px rgba(158, 207, 251, 0.3) !important;
    }
    div[data-testid="stTextInput"] input::placeholder { color: #AAAAAA !important; opacity: 1 !important; }
    div[data-testid="stNumberInput"] button { background-color: transparent !important; border: none !important; color: #AAAAAA !important; font-size: 1.2em !important; padding: 0 5px !important; }
    div[data-testid="stNumberInput"] button:hover { background-color: #EFEFEF !important; color: #666666 !important; }
    div[data-testid="stTextInput"] + div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stNumberInput"] + div[data-testid="stMarkdownContainer"] p {
        font-size: 0.78em !important; color: #888888 !important; margin-top: 0.4em !important; line-height: 1.3 !important;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        border-radius: 5px !important; padding: 10px 20px !important; font-weight: 600 !important;
        border: none !important; box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        transition: background-color 0.2s, box-shadow 0.2s, color 0.2s !important;
        width: fit-content !important;
        background-color: #4CAF50 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #45a049 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }
    div[data-testid="stButton"] button[kind="primary"] > div > div > span {
        color: white !important;
    }
    .stButton > button {
        border-radius: 5px !important; padding: 10px 20px !important; font-weight: 600 !important;
        border: 1px solid #D5D5D5 !important;
        background-color: #F8F9FA !important;
        color: #555555 !important;
        transition: background-color 0.2s, box-shadow 0.2s, color 0.2s !important;
        width: fit-content !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: #E9ECEF !important;
        border-color: #C5C5C5 !important;
        color: #333333 !important;
    }
    .stButton > button > div > div > span {
        white-space: nowrap !important;
    }
    .remove-button > button {
        background-color: #F8F9FA !important;
        border: 1px solid #D5D5D5 !important;
        color: #888888 !important;
        padding: 5px 10px !important;
        box-shadow: none !important;
        height: 100% !important;
    }
    .remove-button > button:hover {
        background-color: #E9ECEF !important;
        color: #333333 !important;
        border-color: #C5C5C5 !important;
    }
    .remove-button > button > div > div > span {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: #888888 !important; /* Ensure the x is gray */
    }
    .remove-button > button:hover > div > div > span {
        color: #333333 !important; /* Darken the x on hover */
    }
    .stTextInput label {
    }
    .remove-button-container {
        display: flex;
        align-items: center; /* Vertically align button with text input */
        height: 100%;
        margin-top: 0 !important;
    }
    .remove-button-container > button {
        height: 100% !important; /* Force button to match container height */
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    .stTextArea {
        border: 1px solid #D5D5D5;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s, border-color 0.2s;
    }
    .stTextArea:focus-within {
        border-color: #9ECFFB !important;
        box-shadow: 0 0 0 2px rgba(158, 207, 251, 0.3) !important;
    }

    /* CUSTOM CSS for button alignment */
    .button-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1.5rem;
    }

    .metric-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 1rem;
        border-radius: 8px;
        background-color: #F8F9FA;
        border: 1px solid #E0E0E0;
        text-align: center;
        height: 100%;
    }

    .metric-value {
        font-size: 2.5em;
        font-weight: 700;
        color: #222;
        margin-top: 0.2em;
    }

    .metric-label {
        font-size: 1em;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    /* Custom styles for the table cells to replace st.column_config.Progress */
    .trend-cell {
        display: flex;
        align-items: center;
    }
    .trend-indicator {
        font-size: 1.5em;
        margin-right: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --- New Function to Merge Scanned Keywords ---
def _merge_scanned_keywords_to_main_list():
    """
    Merges the structured keywords from the AI scan into the main session state structure.
    This preserves category_id and ad_group_id if present in the scanned data,
    but primarily merges by name.
    """
    if "scanned_keywords_structured" not in st.session_state or not st.session_state.scanned_keywords_structured:
        st.toast("⚠️ No scanned keywords to copy.", icon="⚠️")
        return

    scanned_data = st.session_state.scanned_keywords_structured
    current_data = st.session_state.structured_input

    print("SCANNED KEYWORDS", scanned_data)
    print("CURRENT KEYWORDS", current_data)

    new_data = scanned_data[0]['categories']
    for category in new_data:
        for ad_group in category['ad_groups']:
            ad_group['keywords'] = "\n".join(ad_group['keywords'])

    st.session_state.structured_input = new_data

    # Trigger a soft re-run to update the UI with the new structure
    st.session_state.last_action = "merge_scan_data"
    st.toast("✅ Scanned keywords merged into the main list! Remember to save.", icon="📝")
    # No st.rerun() here, as the UI update is often handled by the main loop logic
    # and we want to allow the user to see the change before another action.


# --- Action callbacks ---
def _save_changes():
    """Saves the current state to the database and shows a toast."""
    _autosave_state_to_db()
    st.toast("✅ Changes saved successfully!", icon="💾")


def _run_enrichment():
    """Saves changes and triggers the enrichment pipeline."""
    _autosave_state_to_db()
    st.session_state.enrichment_triggered = True
    st.toast("💡 Saving and starting enrichment pipeline...", icon="🚀")


def _run_analysis_pipeline():
    """Saves changes and triggers the analysis pipeline."""
    _autosave_state_to_db()
    st.session_state.analysis_triggered = True
    st.toast("📊 Saving and starting analysis pipeline...", icon="🚀")


def _render_keyword_input_section():
    display_section_title("Keyword & Ad Group Configuration")

    # Load initial data from the database if not already done
    if "structured_input" not in st.session_state:
        st.session_state.structured_input = []
        _load_db_data_to_state()

    with st.expander("Manage Categories & Ad Groups", expanded=True):
        st.markdown(
            "Build your campaign structure by defining categories, ad groups, and keywords. Your data is automatically loaded and saved to the database.")

    for i, category in enumerate(st.session_state.structured_input):
        category_container = st.container(border=True)
        with category_container:

            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                def remove_category_with_rerun(cat_idx):
                    if 0 <= cat_idx < len(st.session_state.structured_input):
                        # 1. Remove the category
                        # Since the category is indexed by 'i', we can use the index directly.
                        # You'll need to define _remove_category_by_index or adapt your existing one.
                        # For simplicity, let's assume direct deletion based on index:
                        del st.session_state.structured_input[cat_idx]

                        # 2. Clear stale widget states
                        keys_to_delete = []
                        for key in st.session_state.keys():
                            # Clear all states related to the removed index 'cat_idx'
                            # Note: This checks for keys *before* re-indexing.
                            if key.startswith(f"category_name_input_{cat_idx}") or \
                                    key.startswith(f"ad_group_name_input_{cat_idx}_") or \
                                    key.startswith(f"keywords_text_area_{cat_idx}_"):
                                keys_to_delete.append(key)

                        for key in keys_to_delete:
                            del st.session_state[key]

                        # 3. Sync remaining widget states (Re-index remaining items)
                        for new_i, cat in enumerate(st.session_state.structured_input):
                            # Update category name keys
                            st.session_state[f"category_name_input_{new_i}"] = cat["category_name"]

                            for new_j, ag in enumerate(cat["ad_groups"]):
                                # Update ad group name keys
                                st.session_state[f"ad_group_name_input_{new_i}_{new_j}"] = ag["ad_group_name"]
                                # Update keywords text area keys (assuming you have this widget elsewhere)
                                if f"keywords_text_area_{new_i}_{new_j}" in st.session_state:
                                    st.session_state[f"keywords_text_area_{new_i}_{new_j}"] = ag.get("keywords", "")

                category_name_key = f"category_name_input_{i}"
                category_name_value = st.session_state.get(category_name_key, category["category_name"])
                st.text_input(
                    "Category Name",
                    value=category_name_value,
                    key=category_name_key,
                    label_visibility="collapsed",
                    on_change=_update_category_name,
                    args=(i,)
                )
            with col2:
                st.button(
                    "x",
                    on_click=remove_category_with_rerun,
                    args=(i,),  # Pass the index 'i'
                    key=f"remove_category_{i}",  # Use index for key consistency after reruns
                    help="Remove this category",
                    type="secondary",  # Added type for visual consistency
                    use_container_width=False  # Added for visual consistency
                )

            st.markdown("---")

            # Ad Group Loop
            for j, ad_group in enumerate(category["ad_groups"]):
                ad_group_container = st.container(border=True)
                with ad_group_container:
                    ag_col1, ag_col2 = st.columns([0.9, 0.1])
                    with ag_col1:
                        ad_group_name_key = f"ad_group_name_input_{i}_{j}"
                        ad_group_name_value = st.session_state.get(ad_group_name_key, ad_group["ad_group_name"])
                        st.text_input(
                            "Ad Group Name",
                            value=ad_group_name_value,
                            key=ad_group_name_key,
                            label_visibility="collapsed",
                            on_change=_update_ad_group_name,
                            args=(i, j)
                        )
                    with ag_col2:
                        def remove_ad_group_with_rerun(cat_idx, ad_idx):
                            if 0 <= cat_idx < len(st.session_state.structured_input) and 0 <= ad_idx < len(
                                    st.session_state.structured_input[cat_idx]["ad_groups"]):
                                _remove_ad_group(cat_idx, ad_idx)
                                # Clear stale widget states
                                for key in list(st.session_state.keys()):
                                    if key.startswith(f"ad_group_name_input_{cat_idx}_") or key.startswith(
                                            f"keywords_text_area_{cat_idx}_"):
                                        del st.session_state[key]
                                # Sync remaining widget states
                                for new_i, cat in enumerate(st.session_state.structured_input):
                                    st.session_state[f"category_name_input_{new_i}"] = cat["category_name"]
                                    for new_j, ag in enumerate(cat["ad_groups"]):
                                        st.session_state[f"ad_group_name_input_{new_i}_{new_j}"] = ag["ad_group_name"]
                                        st.session_state[f"keywords_text_area_{new_i}_{new_j}"] = ag["keywords"]
                                st.rerun()

                        st.button(
                            "x",
                            on_click=remove_ad_group_with_rerun,
                            args=(i, j),
                            key=f"remove_ad_group_{i}_{j}",
                            help="Remove this ad group",
                            type="secondary",
                            use_container_width=False
                        )

                    st.markdown("---")

                    keywords_key = f"keywords_text_area_{i}_{j}"
                    keywords_value = st.session_state.get(keywords_key, ad_group["keywords"])
                    st.text_area(
                        "Keywords",
                        value=keywords_value,
                        key=keywords_key,
                        height=150,
                        label_visibility="collapsed",
                        on_change=_update_keywords,
                        args=(i, j)
                    )
                    st.markdown("One keyword per line.")

            st.markdown("---")
            st.button("Add Ad Group", on_click=_add_ad_group, args=(i,), key=f"add_ad_group_{i}",
                      use_container_width=True)

    st.markdown("---")
    st.button("Add New Category", on_click=_add_category, key="add_category_main", use_container_width=True)

    # Use a div with a custom class for CSS-based alignment
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    st.button("Save Changes", key="save_changes_button", on_click=_save_changes)
    st.button("Enrich Data", key="enrich_data_button", on_click=_run_enrichment)
    st.button("Run Analysis", key="run_analysis_button", on_click=_run_analysis_pipeline)
    st.markdown('</div>', unsafe_allow_html=True)


def _render_analysis_section():
    """Renders the three-tiered analysis dashboard."""
    display_section_title("Keyword Analysis & Trends")

    # New: Add Country and Language Targeting Settings
    with st.expander("Data Source Settings", expanded=True):
        st.markdown("Define the **geographic country** and **language** for your keyword analysis.")

        # Get country and language options from the imported mappings
        country_options = list(GEO_TARGET_MAP.keys())
        language_options = list(LANGUAGE_MAP.keys())

        # Initialize session state for selected options with a single default value
        if 'country_targeting' not in st.session_state:
            st.session_state.country_targeting = "United States"
        if 'language_targeting' not in st.session_state:
            st.session_state.language_targeting = "English"

        # Use st.selectbox for single selection
        col_country, col_lang = st.columns(2)
        with col_country:
            st.session_state.country_targeting = st.selectbox(
                "Select Country:",
                options=country_options,
                index=country_options.index(st.session_state.country_targeting),
                help="The geographic country to pull keyword data from."
            )
        with col_lang:
            st.session_state.language_targeting = st.selectbox(
                "Select Language:",
                options=language_options,
                index=language_options.index(st.session_state.language_targeting),
                help="The language to filter keyword data by."
            )

    st.markdown("---")

    if not st.session_state.get("analysis_results"):
        st.info("📊 Run the analysis pipeline to view keyword trends and insights here.")
        return

    analyzed_results = st.session_state.analysis_results

    # --- Tier 1: Executive Summary ---
    total_keywords = sum(len(ag['keywords']) for cat in analyzed_results for ag in cat['ad_groups'])
    positive_trend_keywords = sum(
        1 for cat in analyzed_results for ag in cat['ad_groups']
        for kw in ag['keywords'] if kw.get('pct_change_next_month', 0) > 0
    )
    negative_trend_keywords = total_keywords - positive_trend_keywords

    avg_monthly_change = 0
    if total_keywords > 0:
        total_change = sum(
            kw.get('pct_change_next_month', 0) for cat in analyzed_results for ag in cat['ad_groups']
            for kw in ag['keywords']
        )
        avg_monthly_change = total_change / total_keywords

    st.markdown("### Executive Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric(
                label="Overall Monthly Trend",
                value=_format_percentage(avg_monthly_change)
            )

    with col2:
        with st.container(border=True):
            st.metric(
                label="Keywords with Positive Trend",
                value=f"{positive_trend_keywords}"
            )

    with col3:
        with st.container(border=True):
            st.metric(
                label="Keywords with Negative Trend",
                value=f"{negative_trend_keywords}"
            )

    st.markdown("---")

    # --- Tier 2 & 3: Interactive Breakdown & Deep Dive ---
    st.markdown("### Detailed Analysis")
    st.info("📊 Select one or more keywords below to compare their historical trends.")

    # Initialize a list to hold selected keywords if it doesn't exist
    if 'selected_keywords' not in st.session_state:
        st.session_state.selected_keywords = []

    # Store all keywords with unique identifiers for checkboxes
    all_keywords_with_keys = []
    for cat_idx, category in enumerate(analyzed_results):
        for ad_group_idx, ad_group in enumerate(category['ad_groups']):
            for kw_idx, keyword in enumerate(ad_group['keywords']):
                # Create a unique key for each keyword's checkbox
                keyword_key = f"kw_check_{cat_idx}_{ad_group_idx}_{kw_idx}"
                all_keywords_with_keys.append({
                    'keyword': keyword['keyword'],
                    'data': keyword,
                    'checkbox_key': keyword_key
                })

    # Display checkboxes in a structured way (e.g., in expanders)
    for category in analyzed_results:
        with st.expander(f"📁 {category['category']} Analysis"):
            for ad_group in category['ad_groups']:
                with st.expander(f"📦 {ad_group['ad_group']} Ad Group"):
                    # Create a list for the table
                    keyword_data_table = []
                    for keyword in ad_group['keywords']:
                        keyword_data_table.append({
                            'Keyword': keyword['keyword'],
                            '1-Month Forecast': _format_percentage(keyword.get('pct_change_next_month')),
                            '3-Month Forecast': _format_percentage(keyword.get('pct_change_next_3mo')),
                            'Avg. Monthly Searches': f"{int(keyword.get('avg_monthly_searches', 0)):,}",
                            'Seasonal Volatility Score': f"{keyword.get('seasonal_volatility_score', 0):.2f}"
                        })
                    df = pd.DataFrame(keyword_data_table)
                    st.markdown(df.to_html(index=False), unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### Select Keywords to Plot:")

                    # Loop through keywords to create checkboxes
                    cols = st.columns(3)
                    for i, keyword_info in enumerate(ad_group['keywords']):
                        with cols[i % 3]:
                            keyword_label = keyword_info['keyword']
                            # Check if the keyword is already in the selected list
                            is_checked = keyword_info in st.session_state.selected_keywords
                            if st.checkbox(
                                    label=keyword_label,
                                    value=is_checked,
                                    key=f"plot_check_{keyword_info['keyword']}_{ad_group['ad_group']}"
                            ):
                                # Add to selected list if checked and not already there
                                if keyword_info not in st.session_state.selected_keywords:
                                    st.session_state.selected_keywords.append(keyword_info)
                            else:
                                # Remove from selected list if unchecked
                                if keyword_info in st.session_state.selected_keywords:
                                    st.session_state.selected_keywords.remove(keyword_info)

    # --- NEW PLOT LOGIC FOR MULTIPLE KEYWORDS ---
    if st.session_state.selected_keywords:
        st.markdown("---")
        st.markdown(f"### Historical Trend Comparison 📊")
        st.markdown(
            "The chart below shows the **average monthly search volume** for selected keywords based on all historical data, excluding the current year's incomplete data.")

        all_plot_data = []
        months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_year = datetime.now().year
        previous_month = datetime.now().month - 1

        for keyword_info in st.session_state.selected_keywords:
            trend_history = keyword_info.get('trend_history', {})
            monthly_averages = [0] * 12
            month_counts = [0] * 12

            for year_str, months in trend_history.items():
                year = int(year_str)
                # Exclude incomplete data for the current year
                months_to_average = months
                if year == current_year:
                    months_to_average = months[:previous_month]

                for i, volume in enumerate(months_to_average):
                    if i < 12 and volume > 0:  # Ensure index is valid
                        monthly_averages[i] += volume
                        month_counts[i] += 1

            final_averages = [
                monthly_averages[i] / month_counts[i] if month_counts[i] > 0 else 0
                for i in range(12)
            ]

            # Add a data point for each month for the current keyword
            for i, month_name in enumerate(months_names):
                all_plot_data.append({
                    'Month': month_name,
                    'Avg. Search Volume': final_averages[i],
                    'Keyword': keyword_info['keyword']
                })

        if all_plot_data:
            df_trend = pd.DataFrame(all_plot_data)
            fig = px.line(
                df_trend,
                x='Month',
                y='Avg. Search Volume',
                color='Keyword',
                title="Average Monthly Search Volume Comparison"
            )
            fig.update_layout(
                font=dict(family="Segoe UI", size=12, color="#333"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No historical data available for the selected keywords.")

    st.markdown("---")


def run():
    display_header()
    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    # Check for the save, enrichment, and analysis trigger flags
    if 'enrichment_triggered' in st.session_state and st.session_state.enrichment_triggered:
        with st.spinner("Enriching keywords with new ideas..."):
            _perform_enrichment()
            # Sync widget states with updated structured_input
            for i, cat in enumerate(st.session_state.structured_input):
                st.session_state[f"category_name_input_{i}"] = cat["category_name"]
                for j, ag in enumerate(cat["ad_groups"]):
                    st.session_state[f"ad_group_name_input_{i}_{j}"] = ag["ad_group_name"]
                    st.session_state[f"keywords_text_area_{i}_{j}"] = ag["keywords"]
            _autosave_state_to_db()
        st.session_state.enrichment_triggered = False
        st.rerun()

    if 'analysis_triggered' in st.session_state and st.session_state.analysis_triggered:
        with st.spinner("Fetching historical data... This may take some time."):
            # Pass the single country and language selections to the analysis pipeline
            _perform_analysis(
                country=st.session_state.get('country_targeting'),
                language=st.session_state.get('language_targeting')
            )
        st.session_state.analysis_triggered = False
        st.rerun()

    _render_keyword_input_section()

    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    _render_analysis_section()

    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    # --- Website Scanner Section ---
    display_section_title("Website Keyword Scanner")
    with st.expander("Scan a Website for Keywords", expanded=False):
        st.markdown(
            "Enter a website URL to crawl and find keywords using AI. The extracted keywords can be added to your keyword list for analysis.")
        st.markdown("---")

        url_col, depth_col, pages_col, keywords_col = st.columns([2, 1, 1, 1])

        with url_col:
            website_url = st.text_input(
                "Website URL:",
                placeholder="https://www.example.com",
                key="website_url_input",
                help="The starting URL for the scan.",
            )
        with depth_col:
            crawl_depth = st.number_input(
                "Crawl Depth:",
                min_value=1,
                max_value=5,
                value=1,
                key="crawl_depth_input",
                help="The number of link levels to crawl from the starting URL."
            )
        with pages_col:
            max_pages = st.number_input(
                "Max Pages:",
                min_value=1,
                value=5,
                key="max_pages_input",
                help="The maximum number of unique pages to crawl."
            )
        with keywords_col:
            max_keywords = st.number_input(
                "Max Keywords:",
                min_value=10,
                value=50,
                key="max_keywords_input",
                help="The maximum number of keywords to extract. The process stops once this limit is reached.",
            )

        st.markdown("")
        if st.button("Start Scan", key="start_scan_button", use_container_width=True,
                     help="Initiate the keyword scan."):
            if website_url:
                with st.spinner("Running website scan... This may take a few moments."):
                    try:
                        # Pass the current structure for the AI to categorize against
                        scanned_keywords_structured = run_website_scan_cached(
                            website_url.strip(), st.session_state.structured_input, crawl_depth, max_pages, max_keywords
                        )
                        st.session_state.scanned_keywords_structured = scanned_keywords_structured

                        # Calculate total unique keywords found for the success message
                        total_keywords_found = sum(
                            len(ag.get('keywords', [])) for cat in scanned_keywords_structured[0]['categories'] for
                            ag in cat.get('ad_groups', [])
                        )

                        st.success(
                            f"✅ Scan complete! {total_keywords_found} keywords have been categorized into {len(scanned_keywords_structured[0]['categories'])} categories.")
                    except Exception as e:
                        st.error(f"❌ An error occurred during the scan: {e}")
                        logging.error(f"❌ An error occurred during Scanning: {e}", exc_info=True)
                        st.session_state.scanned_keywords_structured = []
            else:
                st.warning("Please enter a valid URL to start the scan.")

        if "scanned_keywords_structured" in st.session_state and st.session_state.scanned_keywords_structured:
            st.markdown("---")
            st.subheader("Extracted Keywords Preview:")

            # --- Display Preview of Scanned Data ---
            print(st.session_state.scanned_keywords_structured)
            for i, category in enumerate(st.session_state.scanned_keywords_structured[0]['categories']):
                with st.expander(
                        f"Category: {category['category_name']} ({len(category.get('ad_groups', []))} Ad Groups)"):
                    for j, ad_group in enumerate(category['ad_groups']):
                        keywords_str = "\n".join(ad_group.get('keywords', ''))
                        keyword_count = len(ad_group.get('keywords', []))
                        st.text_area(
                            f"Ad Group: {ad_group['ad_group_name']} ({keyword_count} keywords)",
                            value=keywords_str,
                            height=100,
                            key=f"scanned_kw_display_{i}_{j}",
                            help="Keywords generated by AI. One keyword per line.",
                            disabled=True
                        )

            # Button to copy keywords to the main list (Now fully functional)
            if st.button("Copy Scanned Categories to Main List", key="copy_scanned_keywords_button",
                         use_container_width=True):
                _merge_scanned_keywords_to_main_list()
                st.rerun()


if __name__ == "__main__":
    run()