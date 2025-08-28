# monthly_notifier.py
from pathlib import Path
import sys
import datetime
import json
from typing import List, Dict, Any

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Imports from core
from core.keyword_expander import expand_keywords_batch
from core.data_provider.google_ads_provider import GoogleAdsProvider
from core.data_provider.fake_provider import FakeProvider
from core.trend_analyzer import TrendAnalyzer
from core.redis_settings import get_keywords_enriched, get_all_settings
from core.slack_notifier import send_alerts_to_slack # Import the new function


def _calculate_historical_average(trend_history: dict) -> float:
    """
    Calculates the average monthly search volume for the current month across all historical years.
    """
    current_month_index = datetime.datetime.now().month - 1
    monthly_volumes = []

    # Iterate through all available years in trend_history
    for year, volumes in trend_history.items():
        # Exclude the current year from the average calculation
        if int(year) < datetime.datetime.now().year and len(volumes) > current_month_index:
            monthly_volumes.append(volumes[current_month_index])

    if not monthly_volumes:
        return 0.0

    return sum(monthly_volumes) / len(monthly_volumes)


def run_analysis_pipeline():
    """
    This script runs the core analysis pipeline:
    1. Gets keywords and settings from Redis.
    2. Expands the keywords.
    3. Fetches trend data using the Google Ads Provider.
    4. Analyzes the trend data.
    5. Injects the historical average into the analysis output.
    6. Returns the final analysis list.
    """
    print("Starting analysis pipeline...")

    # 1. Get keywords and settings from Redis
    keywords_enriched = get_keywords_enriched()
    if not keywords_enriched:
        print("No keywords found in Redis. Exiting.")
        return [], []

    keywords_to_track = [kw['keyword'] for kw in keywords_enriched]

    print(f"Retrieved {len(keywords_to_track)} keywords from Redis.")

    settings = get_all_settings()
    print(f"Loaded settings: {settings}")

    # 2. Expand keywords
    print("Expanding keywords...")
    expanded_keywords = expand_keywords_batch(keywords_to_track, n=2)
    print(f"Expanded keywords to {len(expanded_keywords)} total.")

    # 3. Generate trend data from Google Ads
    print("Generating trend data...")
    # NOTE: Using FakeProvider for local testing to avoid API costs
    # provider = FakeProvider(expanded_keywords)
    provider = GoogleAdsProvider(expanded_keywords)
    enriched_data = provider.generate_output()
    print("Trend data generated successfully.")

    # 4. Analyze the trends
    print("Analyzing trends...")
    analyzer = TrendAnalyzer()
    analysis_results = analyzer.analyze(enriched_data)
    print("Analysis complete.")

    # 5. Inject historical average into analysis results
    for analysis_entry in analysis_results:
        # Find the matching enriched data to get the trend history
        matching_enriched_entry = next(
            (item for item in enriched_data if item["keyword"] == analysis_entry["keyword"]),
            None
        )
        if matching_enriched_entry:
            trend_history = matching_enriched_entry.get("trend_history", {})
            historical_avg = _calculate_historical_average(trend_history)
            analysis_entry["historical_average_monthly_volume"] = historical_avg

    # 6. Return both outputs
    print("Analysis pipeline finished. Returning results.")
    return enriched_data, analysis_results


def extract_alerts_from_analysis(
        results: list[dict],
        min_increase_pct: float = 10.0,
        max_decrease_pct: float = -10.0,
        min_hits_threshold: int = 100
) -> list[dict]:
    """
    Extracts alerts for keywords that meet trend thresholds and a minimum historical average.
    """
    alerts = []

    for entry in results:
        pct_change = entry["total_weighted"]["pct_change_month"]
        historical_average = entry.get("historical_average_monthly_volume", 0)

        # Apply both trend threshold and minimum hits threshold
        if (pct_change >= min_increase_pct or pct_change <= max_decrease_pct) and \
           historical_average >= min_hits_threshold:
            alert = {
                "keyword": entry["keyword"],
                "pct_change_month": round(pct_change, 1),
                "pct_change_3mo": round(entry["total_weighted"]["pct_change_3mo"], 1),
                "historical_average": int(historical_average)
            }
            alerts.append(alert)

    return alerts

def update_campaign_labels(alerts: List[Dict[str, Any]], keywords_enriched: List[Dict[str, Any]]):
    """
    Resets 'Trending Keyword' labels on all campaigns and then applies
    it to campaigns associated with keywords that triggered an alert.
    """
    print("\n" + "=" * 50)
    print("--- UPDATING GOOGLE ADS CAMPAIGN LABELS ---")
    print("=" * 50)

    # Instantiate the provider
    provider = GoogleAdsProvider([])
    label_name = "Trending Keyword"

    # Step 1: Get all campaigns to find which ones have the label
    all_campaigns = provider.get_campaign_data()
    campaign_ids_to_remove_label = [
        c['campaign_id'] for c in all_campaigns if label_name in c.get('labels', [])
    ]

    # Step 2: Remove the label from all campaigns that currently have it
    print(f"Removing '{label_name}' label from {len(campaign_ids_to_remove_label)} campaign(s)...")
    for campaign_id in campaign_ids_to_remove_label:
        provider.set_campaign_label(campaign_id, label_name, "remove")

    # Step 3: Find the campaign IDs for the keywords that triggered an alert
    alert_keywords = {alert['keyword'] for alert in alerts}
    campaign_ids_to_add_label = set()
    for kw_data in keywords_enriched:
        if kw_data['keyword'] in alert_keywords and kw_data.get('campaign_id'):
            campaign_ids_to_add_label.add(kw_data['campaign_id'])

    # Step 4: Add the label to the campaigns that qualify
    print(f"Adding '{label_name}' label to {len(campaign_ids_to_add_label)} campaign(s)...")
    for campaign_id in campaign_ids_to_add_label:
        provider.set_campaign_label(campaign_id, label_name, "add")

    print("Campaign labeling process complete.")


if __name__ == "__main__":
    DRY_RUN = False  # Set False to send actual Slack messages

    enriched_data_output, final_analysis_output = run_analysis_pipeline()

    settings = get_all_settings()
    notification_threshold = settings.get('notification_threshold', 10)
    min_hits_threshold = settings.get('min_hits_threshold', 0)
    slack_webhook_url = settings.get('slack_webhook_url', "")

    print("\n" + "=" * 50)
    print("--- FINAL ANALYSIS OUTPUT (INJECTED AVERAGE) ---")
    print("=" * 50)
    print(json.dumps(final_analysis_output, indent=4))

    # Extract and print the final alerts using the thresholds from settings
    print("\n" + "=" * 50)
    print("--- EXTRACTED ALERTS ---")
    print("=" * 50)
    alerts_to_send = extract_alerts_from_analysis(
        final_analysis_output,
        min_increase_pct=notification_threshold,
        max_decrease_pct=-notification_threshold,
        min_hits_threshold=min_hits_threshold
    )

    print(json.dumps(alerts_to_send, indent=4))

    # Send alerts to Slack if any were found
    if alerts_to_send:
        print("\n" + "=" * 50)
        print("--- SENDING ALERTS TO SLACK ---")
        print("=" * 50)
        send_alerts_to_slack(alerts_to_send, slack_webhook_url, DRY_RUN)
        # Call the new function to update labels
        update_campaign_labels(alerts_to_send, get_keywords_enriched())
    else:
        print("No alerts met the criteria. No messages will be sent.")