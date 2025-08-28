import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional
import time

# Add the project root to sys.path to access core and config
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data_provider.google_ads_provider import GoogleAdsProvider
from core import redis_settings


# --- Helper Functions for UX ---

def get_status_emoji(status: str) -> str:
    """Returns an emoji based on the campaign status."""
    if status == "ENABLED":
        return "✅"
    elif status == "PAUSED":
        return "⏸️"
    elif status == "REMOVED":
        return "🗑️"
    else:
        return "❓"


def get_link_status_emoji(is_linked: bool) -> str:
    """Returns a link status emoji for keywords."""
    return "🔗" if is_linked else "✖️"


def save_all_links():
    """
    Saves all keyword links from session state to Redis.
    """
    if 'keyword_links' in st.session_state:
        redis_settings.save_keyword_campaign_links(st.session_state['keyword_links'])
        st.toast("All changes saved!", icon="💾")
        time.sleep(1)  # Add a small delay for the toast to be seen
    # st.rerun() is not needed here as the app will automatically rerun after the callback completes.


def display_campaign_details(campaign: Dict[str, Any]):
    """
    Displays the details for a single campaign in an expander.
    """
    campaign_status = campaign['campaign_status']
    status_emoji = get_status_emoji(campaign_status)
    labels = campaign.get('labels', [])
    label_text = f" ({', '.join(labels)})" if labels else ""

    with st.expander(f"**{status_emoji} {campaign['campaign_name']}**{label_text} (ID: `{campaign['campaign_id']}`)",
                     expanded=False):
        st.write(f"**Status:** `{campaign_status}`")

        if labels:
            st.write(f"**Labels ({len(labels)}):**")
            st.code(', '.join(labels), language="text")

        st.write(f"**Ad Groups ({len(campaign['ad_groups'])}):**")
        if campaign['ad_groups']:
            ad_groups_df = pd.DataFrame(campaign['ad_groups'])
            ad_groups_df.rename(columns={'ad_group_name': 'Ad Group Name', 'ad_group_id': 'ID'},
                                inplace=True)
            st.dataframe(ad_groups_df, hide_index=True)
        else:
            st.write("No ad groups found.")


# --- Main Page Logic ---

def display_campaign_page():
    """
    Main function to run the Campaigns and Ad Groups page.
    """
    st.set_page_config(layout="wide", page_title="Campaigns & Keywords")
    st.title("Campaigns & Keywords Management")
    st.markdown("---")
    st.write("Link your tracked keywords to specific Google Ads campaigns for better organization and analysis.")

    # Initialize or load the keyword links into session state
    if 'keyword_links' not in st.session_state:
        st.session_state['keyword_links'] = {}

    # Fetch data without caching
    campaign_data = GoogleAdsProvider(data=[]).get_campaign_data()
    keywords_enriched = redis_settings.get_keywords_enriched()

    # Create a mapping for easy lookup
    campaign_options = {None: "Unlink from Campaign"}
    campaign_options.update(
        {c['campaign_id']: f"{get_status_emoji(c['campaign_status'])} {c['campaign_name']}" for c in campaign_data})

    # Store initial state in session_state if it's empty
    if not st.session_state['keyword_links'] and keywords_enriched:
        for kw in keywords_enriched:
            st.session_state['keyword_links'][kw['keyword']] = kw.get('campaign_id')

    # Add a 'is_linked' boolean column and sort by it
    for kw in keywords_enriched:
        kw['is_linked'] = st.session_state['keyword_links'].get(kw['keyword']) is not None

    # Sort: linked keywords first, then unlinked
    keywords_enriched.sort(key=lambda x: (not x['is_linked'], x['keyword']))

    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        st.header("Campaigns & Ad Groups")
        st.info(
            "Here you can view all campaigns fetched from your Google Ads account, including paused ones. Expand a campaign to see its ad groups and labels.")

        if not campaign_data:
            st.warning("No campaign data found. Please check your credentials and network connection.")
        else:
            for campaign in campaign_data:
                display_campaign_details(campaign)

    with col2:
        st.header("Link Keywords to Campaigns")
        st.info(
            "Use the dropdowns to assign each keyword to a campaign. Your changes are saved in memory and can be committed by clicking the 'Save Changes' button.")
        st.markdown("---")

        if not keywords_enriched:
            st.warning("No keywords found in the database. Please add some on the main page.")
        else:
            header_cols = st.columns([0.1, 0.4, 0.5])
            with header_cols[0]:
                st.markdown("**Status**")
            with header_cols[1]:
                st.markdown("**Keyword**")
            with header_cols[2]:
                st.markdown("**Link Campaign**")

            # Display each keyword with a dropdown for linking
            for keyword_data in keywords_enriched:
                keyword = keyword_data['keyword']

                cols = st.columns([0.1, 0.4, 0.5])

                with cols[0]:
                    st.markdown(get_link_status_emoji(keyword_data['is_linked']))
                with cols[1]:
                    st.markdown(f"**{keyword}**")

                with cols[2]:
                    # Find the correct initial index for the selectbox
                    options_list = list(campaign_options.keys())
                    current_campaign_id = st.session_state['keyword_links'].get(keyword)
                    initial_index = options_list.index(
                        current_campaign_id) if current_campaign_id in options_list else 0

                    st.selectbox(
                        label="select campaign",
                        options=options_list,
                        format_func=lambda x: campaign_options[x],
                        index=initial_index,
                        label_visibility="collapsed",
                        key=f"selectbox_{keyword}",
                        on_change=lambda kw=keyword: st.session_state['keyword_links'].update(
                            {kw: st.session_state[f"selectbox_{kw}"]})
                    )

        st.markdown("---")
        st.button("Save All Changes", on_click=save_all_links, use_container_width=True)


if __name__ == "__main__":
    display_campaign_page()