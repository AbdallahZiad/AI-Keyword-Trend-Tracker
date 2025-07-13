import requests
from config.settings import SLACK_WEBHOOK_URL

def send_slack_message(text: str):
    payload = {"text": text}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        raise Exception(f"Slack API error {response.status_code}: {response.text}")

def format_alert_message(alert: dict) -> str:
    """Formats a single alert dict into a Slack-friendly message."""
    arrow = "📈" if alert["pct_change_month"] > 0 else "📉"
    keyword = alert["keyword"]

    message = (
        f"*{arrow} Keyword Alert: `{keyword}`*\n"
        f"> Current Volume: *{alert['current']}*\n"
        f"> Expected Next Month: *{alert['expected_next_month']}* "
        f"({alert['pct_change_month']}%)\n"
        f"> 3-Month Forecast Avg: *{alert['expected_next_3mo_avg']}* "
        f"({alert['pct_change_3mo']}%)"
    )

    return message


def send_alerts_to_slack(alerts: list[dict], dry_run: bool = False) -> None:
    """Sends all filtered alerts to Slack using the client."""
    for alert in alerts:
        message = format_alert_message(alert)
        if dry_run:
            print(f"\n[DRY RUN] Would send:\n{message}")
        else:
            send_slack_message(message)