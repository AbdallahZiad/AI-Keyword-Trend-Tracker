import streamlit as st
import redis
import os
import json
from typing import List, Dict, Any, Optional

# --- Constants & Initialization ---
SETTINGS_KEY = "dashboard_settings"
KEYWORDS_KEY = "tracked_keywords"


def get_redis_client():
    """Establishes and returns a Redis client connection using Streamlit secrets."""
    try:
        # First, try to get the URL from Streamlit secrets (for dashboard)
        if "REDIS_URL" in st.secrets:
            redis_url = st.secrets["REDIS_URL"]
        # Fallback to environment variable (for local script execution)
        elif "REDIS_URL" in os.environ:
            redis_url = os.environ["REDIS_URL"]
        else:
            raise ValueError("REDIS_URL not found in Streamlit secrets or environment variables.")
        return redis.from_url(redis_url)
    except Exception as e:
        st.error(f"Error connecting to Redis: {e}")
        return None


def initialize_redis_settings(force=False):
    """
    Initializes the Redis database with default settings if they don't exist.
    Use force=True to reset the settings.
    """
    r = get_redis_client()
    if r is None:
        return

    # Check if settings already exist
    if not force and r.exists(SETTINGS_KEY):
        st.info("Database already initialized with settings.")
        return

    # Set default values
    default_settings = {
        "notification_threshold": 10,
        "min_hits_threshold": 100,
        "slack_webhook_url": ""
    }
    r.set(SETTINGS_KEY, json.dumps(default_settings))
    # Keywords are now stored as a list of dictionaries to include campaign ID
    r.set(KEYWORDS_KEY, json.dumps([]))
    st.success("Database initialized with default settings and empty keywords!")
    print("Database initialized with default settings and empty keywords.")


def get_all_settings():
    """Retrieves all settings from the Redis database."""
    r = get_redis_client()
    if r is None:
        return {}

    settings_json = r.get(SETTINGS_KEY)
    settings = json.loads(settings_json) if settings_json else {}

    keywords_json = r.get(KEYWORDS_KEY)
    settings["tracked_keywords"] = json.loads(keywords_json) if keywords_json else []

    return settings


def get_keywords() -> List[str]:
    """
    Retrieves the tracked keywords from the Redis database and returns a simple list of strings.
    This ensures backward compatibility with app.py.
    """
    r = get_redis_client()
    if r is None:
        return []

    keywords_json = r.get(KEYWORDS_KEY)
    if not keywords_json:
        return []

    # The stored data is now a list of dictionaries, so we extract the 'keyword' value
    keywords_list_enriched = json.loads(keywords_json)
    return [kw_data['keyword'] for kw_data in keywords_list_enriched]


def save_all_settings(notification_threshold: int, min_hits_threshold: int, slack_webhook_url: str):
    """Saves all settings to the Redis database."""
    r = get_redis_client()
    if r is None:
        return False

    settings_to_save = {
        "notification_threshold": notification_threshold,
        "min_hits_threshold": min_hits_threshold,
        "slack_webhook_url": slack_webhook_url
    }
    try:
        r.set(SETTINGS_KEY, json.dumps(settings_to_save))
        return True
    except Exception as e:
        st.error(f"Error saving settings to Redis: {e}")
        return False


def save_keywords(keywords: List[str]):
    """
    Saves the tracked keywords to the Redis database while preserving existing campaign associations.
    This is the method called by app.py.
    """
    r = get_redis_client()
    if r is None:
        return False

    # Retrieve the full enriched list to preserve campaign associations
    keywords_list_enriched = get_keywords_enriched()
    existing_map = {kw['keyword']: kw.get('campaign_id') for kw in keywords_list_enriched}

    # Format the new list of keywords, adding campaign_id if it existed
    keywords_to_save = []
    for keyword in keywords:
        campaign_id = existing_map.get(keyword)
        keywords_to_save.append({
            "keyword": keyword,
            "campaign_id": campaign_id
        })

    try:
        r.set(KEYWORDS_KEY, json.dumps(keywords_to_save))
        return True
    except Exception as e:
        st.error(f"Error saving keywords to Redis: {e}")
        return False


def get_keywords_enriched() -> List[Dict[str, Any]]:
    """
    Retrieves the full list of tracked keywords with their campaign data.
    This is for internal use where the enriched data is needed.
    """
    r = get_redis_client()
    if r is None:
        return []
    keywords_json = r.get(KEYWORDS_KEY)
    return json.loads(keywords_json) if keywords_json else []


def save_keyword_campaign_links(links: Dict[str, Optional[int]]):
    """
    Saves a batch of keyword-campaign links to the Redis database.
    """
    r = get_redis_client()
    if r is None:
        return False

    # Get the current list of keywords from Redis to preserve other data
    current_keywords = get_keywords_enriched()
    current_map = {kw['keyword']: kw for kw in current_keywords}

    # Create the new list, updating campaign IDs based on the provided links
    updated_keywords = []
    for keyword, campaign_id in links.items():
        if keyword in current_map:
            # Update the existing dictionary
            entry = current_map[keyword]
            entry['campaign_id'] = campaign_id
            updated_keywords.append(entry)
        else:
            # If the keyword doesn't exist yet, add it
            updated_keywords.append({
                "keyword": keyword,
                "campaign_id": campaign_id
            })

    # We must also re-add any keywords that were not in the 'links' dictionary
    # to avoid overwriting the entire list.
    for keyword, entry in current_map.items():
        if keyword not in links:
            updated_keywords.append(entry)

    try:
        r.set(KEYWORDS_KEY, json.dumps(updated_keywords))
        return True
    except Exception as e:
        st.error(f"Error saving keyword-campaign links to Redis: {e}")
        return False