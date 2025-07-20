import streamlit as st
import pandas as pd
from ui_helpers import format_percentage, display_header, display_section_title

import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports from core
from core.keyword_expander import expand_keywords_batch
from core.data_provider.fake_provider import FakeProvider
from core.trend_analyzer import TrendAnalyzer

# Define the path to keywords.txt relative to the app.py location
KEYWORDS_FILE_PATH = project_root / "data" / "keywords.txt"

# Function to load keywords (copied from main.py)
def load_keywords_from_txt(path: Path) -> list[str]:
    abs_path = path.resolve()
    if not abs_path.exists():
        st.error(f"Error: Keywords file not found at {abs_path}")
        return []
    with open(abs_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# --- Streamlit Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Keyword Category Trend Monitor",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for specific styling (remains unchanged) ---
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
    div[data-testid="stMarkdownContainer"] table {
        width: 100% !important; border-collapse: separate !important; border-spacing: 0 !important;
        border: 1px solid #E0E0E0 !important; border-radius: 6px !important; overflow: hidden !important;
        margin-top: 1.5rem !important; margin-bottom: 3.0rem !important; box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
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
        color: #777777 !important; font-style: italic !important; height: 250px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
    }
    .stButton > button {
        border-radius: 5px !important; padding: 10px 20px !important; font-weight: 600 !important;
        border: none !important; box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        transition: background-color 0.2s, box-shadow 0.2s, color 0.2s !important;
        width: fit-content !important; display: inline-block !important;
    }
    .stButton > button:hover {
        background-color: #45a049 !important; box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }
    div[data-testid="stButton"] > button:hover > div > div > span { color: white !important; }
    div.stButton { margin-top: 2rem !important; }
    </style>
    """,
    unsafe_allow_html=True
)


def run():
    display_header()
    st.markdown("<div class='page-divider'></div>", unsafe_allow_html=True)

    # Load keywords
    st.subheader("Loaded Keywords (from keywords.txt):")
    loaded_keywords = load_keywords_from_txt(KEYWORDS_FILE_PATH)
    if loaded_keywords:
        st.write(loaded_keywords)
    else:
        st.warning("No keywords loaded or file not found.")
    st.markdown("---") # Visual separator

    # Expand keywords
    st.subheader("Expanded Keywords:")
    expanded_keywords = []
    if loaded_keywords:
        with st.spinner("Expanding keywords..."):
            expanded_keywords = expand_keywords_batch(loaded_keywords)
        st.write(expanded_keywords)
    else:
        st.info("No keywords to expand.")
    st.markdown("---") # Visual separator

    # Generate fake trend data using FakeProvider
    st.subheader("Fake Trend Data (Generated by FakeProvider):")
    enriched_data = []
    if expanded_keywords:
        with st.spinner("Generating fake trend data..."):
            provider = FakeProvider(expanded_keywords)
            enriched_data = provider.generate_fake_output()
        st.write(enriched_data[:5]) # Displaying a slice as output can be large
        if len(enriched_data) > 5:
            st.info(f"Showing first 5 entries out of {len(enriched_data)} generated data points.")
    else:
        st.info("No keywords to generate fake data for.")
    st.markdown("---") # Visual separator

    # Analyze trends
    st.subheader("Analysis Results (from TrendAnalyzer):")
    analysis_results_for_table = [] # Renamed for clarity, will be used to populate table
    if enriched_data:
        with st.spinner("Analyzing trends..."):
            analyzer = TrendAnalyzer()
            analysis_results_for_table = analyzer.analyze(enriched_data)
        st.write(analysis_results_for_table[:5]) # Displaying a slice for debug/preview
        if len(analysis_results_for_table) > 5:
            st.info(f"Showing first 5 entries out of {len(analysis_results_for_table)} analyzed results.")
    else:
        st.info("No data to analyze.")
    st.markdown("---") # Visual separator


    # --- DYNAMICALLY POPULATING THE TABLE WITH ANALYSIS RESULTS ---
    # The hardcoded 'analyzed_trend_data' is now removed.

    display_section_title("Tracked Categories & Keywords")

    table_data = []
    # Loop through the dynamically generated analysis_results_for_table
    for item in analysis_results_for_table:
        # Assuming TrendAnalyzer output keys are: 'keyword', 'current', 'pct_change_month', 'pct_change_3mo'
        # If your TrendAnalyzer uses different keys (e.g., 'current_volume', 'percentage_change_30_days'),
        # you will need to adjust these key names accordingly to match the table display.
        keyword = item.get('keyword', 'N/A')
        current_volume = item.get('current', 0)
        pct_change_month = item.get('pct_change_month')
        pct_change_3mo = item.get('pct_change_3mo')

        trend_arrow_html = ""
        if pct_change_month is not None:
            if pct_change_month > 0:
                trend_arrow_html = "<span style='color:green; font-weight: bold;'>↑</span>"
            elif pct_change_month < 0:
                trend_arrow_html = "<span style='color:red; font-weight: bold;'>↓</span>"
            else:
                trend_arrow_html = "<span>―</span>"

        # Keep the display keyword logic for specific mappings if desired
        display_keyword = keyword
        if keyword == 'ai marketing':
            display_keyword = 'AI Tools'
        elif keyword == 'gaming laptop':
            display_keyword = 'Gaming Laptops'
        # You might want to remove or adjust this logic if your keywords.txt becomes very dynamic
        # and you don't have fixed mappings.

        table_data.append({
            "SELECT": f"<input type='checkbox' id='select_{keyword.replace(' ', '_')}' name='select_{keyword.replace(' ', '_')}'>",
            "CATEGORY/KEYWORD": display_keyword,
            "CURRENT VOLUME": f"{current_volume:,}",
            "% CHANGE (30 DAYS)": format_percentage(pct_change_month) if pct_change_month is not None else "",
            " % CHANGE (90 DAYS)": format_percentage(pct_change_3mo) if pct_change_3mo is not None else "",
            "TREND": trend_arrow_html
        })

    df = pd.DataFrame(table_data)
    if not df.empty:
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No trend data available to display in the table.")


    display_section_title("Trend History (Selected Category)")
    st.markdown(
        """
        <div style="
            background-color: #F8F8F8;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 3rem;
            text-align: center;
            color: #777777;
            font-style: italic;
            height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            Graph Placeholder Here
        </div>
        """,
        unsafe_allow_html=True
    )

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

    # Button alignment
    button_col, _ = st.columns([0.5, 2])

    with button_col:
        if st.button("Save Settings"):
            st.toast("Settings saved successfully!", icon="✅")

if __name__ == "__main__":
    run()