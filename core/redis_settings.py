import streamlit as st
import redis
import os
import json

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


def get_keywords():
    """Retrieves the tracked keywords from the Redis database."""
    r = get_redis_client()
    if r is None:
        return []

    keywords_json = r.get(KEYWORDS_KEY)
    return json.loads(keywords_json) if keywords_json else []


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


def save_keywords(keywords: list[str]):
    """Saves the tracked keywords to the Redis database."""
    r = get_redis_client()
    if r is None:
        return False

    try:
        r.set(KEYWORDS_KEY, json.dumps(keywords))
        return True
    except Exception as e:
        st.error(f"Error saving keywords to Redis: {e}")
        return False


if __name__ == '__main__':
    print("Running Redis settings initialization script.")
    initialize_redis_settings()