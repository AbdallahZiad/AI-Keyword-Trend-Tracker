import streamlit as st
import pandas as pd
from ui_helpers import format_percentage, display_header, display_section_title

import os
import sys
from pathlib import Path
import datetime
import altair as alt

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports from core
from core.keyword_expander import expand_keywords_batch
from core.data_provider.google_ads_provider import GoogleAdsProvider
from core.trend_analyzer import TrendAnalyzer

# Define the path to keywords.txt relative to the app.py location
KEYWORDS_FILE_PATH = project_root / "data" / "keywords.txt"

# --- GLOBAL SETTINGS ---
DEBUG_MODE = True  # Set to True to show pipeline status and expanded data sections


# --- Functions (some cached for performance, some not) ---
def load_keywords_from_txt(path: Path) -> list[str]:
    """
    Loads keywords from a text file.
    This function is NOT cached as the file content can change externally.
    """
    abs_path = path.resolve()
    if not abs_path.exists():
        return []
    with open(abs_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


@st.cache_data(show_spinner=False)
def get_expanded_keywords_cached(loaded_keywords: list[str]) -> list[str]:
    """
    Expands keywords. Cached, as expansion depends only on loaded keywords.
    Cache busts if 'loaded_keywords' list changes.
    """
    return expand_keywords_batch(loaded_keywords, n=2)


@st.cache_data(show_spinner=False)
def get_enriched_data_cached(expanded_keywords: list[str], current_period_id: str):
    """
    Generates trend data. Cached, but cache busts if 'expanded_keywords'
    change OR if the 'current_period_id' (current day/month/year) changes.
    """
    provider = GoogleAdsProvider(expanded_keywords)
    return provider.generate_output()


@st.cache_data(show_spinner=False)
def get_analysis_results_cached(enriched_data: list[dict]):
    """
    Analyzes trend data. Cached, as analysis depends only on enriched data.
    Cache busts if 'enriched_data' changes (i.e., new day/month or new keywords).
    """
    analyzer = TrendAnalyzer()
    return analyzer.analyze(enriched_data)


# --- Streamlit Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Keyword Category Trend Monitor",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for specific styling ---
st.markdown(
    """
    <style>
    body { background-color: #F0F2F6 !important; color: #333333 !important; }
    .stApp > div:first-child > section.main {
        background-color: white !important; padding: 35px !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06) !important; margin: 25px auto !important;
        max-width: 900px !important; width: 95% !important;
    }
    header, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-right: 2.5rem !important; padding-left: 2.5rem !important; padding-bottom: 1.5rem !important; }
    h1 { font-size: 2.2em !important; margin-bottom: 0.8rem !important; color: #222222 !important; font-weight: 700 !important; }
    h2 { font-size: 1.3em !important; margin-top: 2.8rem !important; margin-bottom: 0.9rem !important; color: #333333 !important; font-weight: 600 !important; }
    h3 { font-size: 1.0em !important; color: #555555 !important; margin-bottom: 0.5rem !important; font-weight: 500 !important; }
    p, label, .stMarkdown, .stNumberInput, .stTextInput { font-family: 'Segoe UI', Arial, sans-serif !important; color: #555555 !important; line-height: 1.5 !important; }
    .page-divider { border-bottom: 1px solid #D5D5D5 !important; margin-bottom: 2rem; width: 100%; }

    /* ORIGINAL TABLE CSS */
    div[data-testid="stMarkdownContainer"] table {
        width: 100% !important; border-collapse: separate !important; border-spacing: 0 !important;
        border: 1px solid #E0E0E0 !important; border-radius: 6px !important;
        margin-top: 1.5rem !important; margin-bottom: 3.0rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    }

    /* Responsive wrapper for tables */
    .table-responsive-wrapper {
        width: 100%;
        overflow-x: auto; /* Enable horizontal scrolling */
        -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
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
    .stMarkdown div[style*="height: 250px"] {
        background-color: #F8F8F8 !important; border: 1px solid #E0E0E0 !important; border-radius: 8px !important;
        padding: 20px !important; margin-bottom: 3rem !important; text-align: center !important;
        color: #777777 !important; font-style: italic; height: 250px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
    }

    /* General styling for Streamlit buttons */
    .stButton > button {
        border-radius: 5px !important; padding: 10px 20px !important; font-weight: 600 !important;
        border: none !important; box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        transition: background-color 0.2s, box-shadow 0.2s, color 0.2s !important;
        width: fit-content !important;
    }
    .stButton > button:hover {
        background-color: #45a049 !important; box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }
    div[data-testid="stButton"] > button:hover > div > div > span { color: white !important; }

    /* Ensure button text never wraps */
    .stButton > button > div > div > span {
        white-space: nowrap !important;
    }

    /* Reset default Streamlit button container margin and width */
    div[data-testid="stButton"] {
        margin: 0 !important; /* Remove all default margins from individual button containers */
        min-width: unset !important; /* Ensure they don't have a minimum width forcing wrap */
        max-width: unset !important; /* Ensure they don't have a maximum width forcing wrap */
    }

    /* Custom Container for Keywords Buttons - Using Flexbox for robust alignment */
    .button-container-keywords {
        display: flex !important; /* Ensure flex is applied */
        align-items: center !important; /* Vertically align items in the center */
        width: 100% !important; /* Take full available width */
        margin-top: 2rem !important; /* Add desired top margin for the entire button group */
        flex-wrap: nowrap !important; /* IMPORTANT: Prevent buttons from wrapping to a new line */
        /* justify-content: flex-start; is the default for flex, so no need to explicitly set it here */
    }

    /* Specific child rules removed as only one button remains in the container */
    </style>
    """,
    unsafe_allow_html=True
)


def run():
    display_header()
    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    # --- Keyword Management Section ---
    display_section_title("Keyword Management")

    if "active_keywords_for_analysis" not in st.session_state:
        default_keywords_list = load_keywords_from_txt(KEYWORDS_FILE_PATH)
        st.session_state.active_keywords_for_analysis = "\n".join(default_keywords_list)
        st.session_state.editable_keywords_text = st.session_state.active_keywords_for_analysis

    with st.expander("Configure Keywords", expanded=True):
        st.markdown("Enter keywords below, one per line. These will be used for analysis.")
        st.markdown("---")

        edited_keywords_raw = st.text_area(
            "Keywords List:",
            value=st.session_state.editable_keywords_text,
            height=200,
            help="Type or paste keywords, **one per line**. Click 'Apply Keywords' below to update.",
            key="keywords_text_input_raw"
        )

        if edited_keywords_raw != st.session_state.editable_keywords_text:
            st.session_state.editable_keywords_text = edited_keywords_raw

        st.markdown('<div class="button-container-keywords">', unsafe_allow_html=True)

        if st.button("Apply Keywords", key="apply_keywords_button"):
            if st.session_state.editable_keywords_text != st.session_state.active_keywords_for_analysis:
                st.session_state.active_keywords_for_analysis = st.session_state.editable_keywords_text
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        uploaded_file = st.file_uploader(
            "Or upload a keywords.txt file:",
            type=["txt"],
            help="Uploading a plain text (.txt) file will overwrite the keywords in the text area above and automatically trigger analysis. Ensure it's UTF-8 encoded with one keyword per line.",
            key="keyword_file_uploader"
        )

        if uploaded_file is not None:
            try:
                file_contents = uploaded_file.read().decode("utf-8")
                if file_contents != st.session_state.active_keywords_for_analysis or \
                        file_contents != st.session_state.editable_keywords_text:
                    st.session_state.editable_keywords_text = file_contents
                    st.session_state.active_keywords_for_analysis = file_contents
                    st.rerun()

            except UnicodeDecodeError:
                st.error("Error: Could not decode the file. Please ensure it is a plain text file (UTF-8 encoded).")
            except Exception as e:
                st.error(f"An unexpected error occurred while reading the file: {e}")

    loaded_keywords = [
        kw.strip() for kw in st.session_state.active_keywords_for_analysis.split('\n') if kw.strip()
    ]

    if not loaded_keywords:
        st.warning("No keywords provided. Please enter keywords above or upload a file to proceed.")
        st.stop()

    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    current_day_month_year_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # --- Data Pipeline Execution ---
    with st.spinner("Expanding keywords..."):
        expanded_keywords = get_expanded_keywords_cached(loaded_keywords)

    with st.spinner("Generating trend data..."):
        enriched_data = get_enriched_data_cached(expanded_keywords, current_day_month_year_str)

    with st.spinner("Analyzing trends..."):
        analysis_results_for_table = get_analysis_results_cached(enriched_data)

    # --- Debugging/Pipeline Status Sections (only shown in DEBUG_MODE) ---
    if DEBUG_MODE:
        st.subheader("Debugging & Pipeline Status")
        with st.expander("Show Loaded Keywords (from current input)", expanded=True):
            if loaded_keywords:
                st.write(loaded_keywords)
            else:
                st.info("No keywords loaded from input.")
        st.markdown("---")

        with st.expander("Show Expanded Keywords", expanded=True):
            if expanded_keywords:
                st.write(expanded_keywords)
            else:
                st.info("No keywords to expand.")
        st.markdown("---")

        with st.expander("Show Generated Trend Data", expanded=True):
            if enriched_data:
                st.write(enriched_data[:5])
                if len(enriched_data) > 5:
                    st.info(f"Showing first 5 entries out of {len(enriched_data)} generated data points.")
            else:
                st.info("No keywords to generate data for.")
        st.markdown("---")

        with st.expander("Show Analysis Results", expanded=True):
            if analysis_results_for_table:
                st.write(analysis_results_for_table[:5])
                if len(analysis_results_for_table) > 5:
                    st.info(f"Showing first 5 entries out of {len(analysis_results_for_table)} analyzed results.")
            else:
                st.info("No data to analyze.")
        st.markdown("---")

    # --- DYNAMICALLY POPULATING THE TABLE WITH ANALYSIS RESULTS ---
    display_section_title("Tracked Categories & Keywords")

    table_data = []
    available_keywords = []

    # Get the current month to average over
    current_month_index = datetime.datetime.now().month - 1
    years_to_average = [2022, 2023, 2024]

    for item in analysis_results_for_table:
        keyword = item.get('keyword', 'N/A')
        available_keywords.append(keyword)

        pct_change_month = item.get('pct_change_month')
        pct_change_3mo = item.get('pct_change_3mo')

        # --- Calculate Expected Monthly Volume ---
        expected_volume = 0
        valid_years_count = 0

        # Find the full trend history from enriched_data
        full_trend_history = next(
            (enriched_item.get('trend_history') for enriched_item in enriched_data if
             enriched_item.get('keyword') == keyword),
            None
        )

        if full_trend_history:
            for year in years_to_average:
                if year in full_trend_history and len(full_trend_history[year]) > current_month_index:
                    expected_volume += full_trend_history[year][current_month_index]
                    valid_years_count += 1

        if valid_years_count > 0:
            expected_volume = round(expected_volume / valid_years_count)
        else:
            expected_volume = 0
        # --- End of calculation ---

        trend_arrow_html = ""
        if pct_change_month is not None:
            if pct_change_month > 0:
                trend_arrow_html = "<span style='color:green; font-weight: bold;'>↑</span>"
            elif pct_change_month < 0:
                trend_arrow_html = "<span style='color:red; font-weight: bold;'>↓</span>"
            else:
                trend_arrow_html = "<span>―</span>"

        table_data.append({
            "CATEGORY/KEYWORD": keyword,
            "EXPECTED MONTHLY VOLUME": f"{expected_volume:,}",
            "% CHANGE (30 DAYS)": format_percentage(pct_change_month) if pct_change_month is not None else "",
            " % CHANGE (90 DAYS)": format_percentage(pct_change_3mo) if pct_change_3mo is not None else "",
            "TREND": trend_arrow_html
        })

    df = pd.DataFrame(table_data)
    if not df.empty:
        st.markdown(
            f"""
            <div class="table-responsive-wrapper">
                {df.to_html(escape=False, index=False)}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No trend data available to display in the table.")

    # --- Checkbox Selection for Graph ---
    display_section_title("Select Keywords for Trend Graph")

    selected_keywords_for_graph = []
    if available_keywords:
        for i, kw in enumerate(available_keywords):
            if f"checkbox_{kw.replace(' ', '_')}" not in st.session_state:
                st.session_state[f"checkbox_{kw.replace(' ', '_')}"] = (i == 0)

        cols = st.columns(4)
        for i, kw in enumerate(available_keywords):
            with cols[i % 4]:
                if st.checkbox(kw, key=f"checkbox_{kw.replace(' ', '_')}"):
                    selected_keywords_for_graph.append(kw)
    else:
        st.info("No keywords available to select for the graph.")

    # --- TREND HISTORY GRAPH ---
    display_section_title("Trend History (Selected Categories)")

    if selected_keywords_for_graph and enriched_data:
        dfs_to_concat = []
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        for keyword_to_plot in selected_keywords_for_graph:
            selected_trend_history = next(
                (item.get('trend_history') for item in enriched_data if item.get('keyword') == keyword_to_plot), None)

            if selected_trend_history:
                years_to_average = [2022, 2023, 2024]
                monthly_averages = [0] * 12
                valid_years_count = 0

                for year in years_to_average:
                    if year in selected_trend_history:
                        for month_index, volume in enumerate(selected_trend_history[year]):
                            monthly_averages[month_index] += volume
                        valid_years_count += 1

                if valid_years_count > 0:
                    monthly_averages = [round(v / valid_years_count) for v in monthly_averages]

                    kw_df = pd.DataFrame({
                        "Month": month_names,
                        keyword_to_plot: monthly_averages
                    })
                    kw_df = kw_df.set_index("Month")
                    dfs_to_concat.append(kw_df)
            else:
                st.warning(f"No trend history found for '{keyword_to_plot}'.")

        if dfs_to_concat:
            final_graph_df = pd.concat(dfs_to_concat, axis=1)
            final_graph_df.index.name = 'Month'
            final_graph_df.reset_index(inplace=True)

            df_long = pd.melt(
                final_graph_df,
                id_vars='Month',
                var_name='Keyword',
                value_name='Average Monthly Volume'
            )

            chart = alt.Chart(df_long).mark_line(point=True).encode(
                x=alt.X('Month:N', sort=month_names, title='Month'),
                y=alt.Y('Average Monthly Volume:Q', title='Average Search Volume'),
                color=alt.Color('Keyword:N', title='Keyword')
            ).properties(
                title='Average Monthly Search Volume Trends (2022-2024)'
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No selected keywords have complete trend data to display.")

    elif not selected_keywords_for_graph:
        st.info("Please select at least one keyword above to see its trend history.")
    else:
        st.info("Please ensure keywords are loaded and data is generated to see trend history.")

    # --- SETTINGS & CONFIGURATION ---
    display_section_title("Settings & Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Notification Threshold (% Change):")
        notification_threshold = st.number_input(
            "Hidden label for notification threshold.",
            min_value=0,
            max_value=100,
            value=10,
            label_visibility="collapsed",
            key="notification_threshold_input"
        )
        st.markdown("Notify if search volume changes by this percentage.")

    with col2:
        st.subheader("Slack Webhook URL:")
        slack_webhook_url = st.text_input(
            "Hidden label for Slack webhook URL.",
            value="",
            placeholder="Enter Slack webhook URL",
            label_visibility="collapsed",
            key="slack_webhook_url_input"
        )
        st.markdown("Notifications will be sent to this Slack channel.")

    button_col, _ = st.columns([0.5, 2])

    with button_col:
        if st.button("Save Settings"):
            st.toast("Settings saved successfully!", icon="✅")


if __name__ == "__main__":
    run()