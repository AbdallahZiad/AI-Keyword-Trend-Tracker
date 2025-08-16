import requests
from config.settings import SLACK_WEBHOOK_URL

def send_slack_message(text: str, webhook_url: str):
    """
    Sends a message to a Slack channel using a specified webhook URL.

    Args:
        text (str): The message text to send.
        webhook_url (str): The Slack webhook URL to send the message to.
    """
    payload = {"text": text}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        # Catch and handle specific request exceptions for better error reporting
        raise Exception(f"Failed to send Slack message: {e}") from e


def format_alert_message(alert: dict) -> str:
    """Formats a single alert dict into a Slack-friendly message."""
    arrow = "📈" if alert["pct_change_month"] > 0 else "📉"
    keyword = alert["keyword"]

    # Use the new 'historical_average' field for the volume.
    historical_avg = alert.get("historical_average", "N/A")

    # Format the message to be clear and use all data points.
    message = (
        f"*{arrow} Keyword Alert: `{keyword}`*\n"
        f"> Monthly % Change: `{alert['pct_change_month']}%`\n"
        f"> 3-Month % Change: `{alert['pct_change_3mo']}%`\n"
        f"> Expected Monthly Volume: `{historical_avg}`"
    )

    return message

def send_alerts_to_slack(alerts: list[dict], webhook_url: str, dry_run: bool = False) -> None:
    """
    Sends a list of alerts to Slack.

    Args:
        alerts (list[dict]): The list of alert dictionaries to send.
        webhook_url (str): The Slack webhook URL to send the messages to.
        dry_run (bool): If True, messages are printed instead of being sent.
    """
    if not alerts:
        print("No alerts to send.")
        return

    for alert in alerts:
        message = format_alert_message(alert)
        if dry_run:
            print(f"\n[DRY RUN] Would send:\n{message}")
        else:
            try:
                # Pass the webhook_url to the send_slack_message function
                send_slack_message(message, webhook_url)
                print(f"Successfully sent alert for '{alert['keyword']}'.")
            except Exception as e:
                print(f"Failed to send alert for '{alert['keyword']}': {e}")