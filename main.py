import argparse
import json
from core.keyword_expander import expand_keywords_batch
from core.data_provider.fake_provider import FakeProvider
from core.trend_analyzer import TrendAnalyzer
from core.transformers import extract_alerts_from_analysis
from core.slack_notifier import send_alerts_to_slack

def load_keywords_from_txt(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def main():
    parser = argparse.ArgumentParser(description="Run full trend alert pipeline.")
    parser.add_argument("keywords_file", help="Path to a .txt file with one keyword per line")
    parser.add_argument("--min-increase", type=float, default=10.0, help="Min % increase for alert")
    parser.add_argument("--max-decrease", type=float, default=-10.0, help="Max % decrease for alert")
    parser.add_argument("--dry-run", action="store_true", help="Print alerts instead of sending to Slack")

    args = parser.parse_args()

    print("📥 Loading keywords...")
    raw_keywords = load_keywords_from_txt(args.keywords_file)

    print("🔍 Expanding keywords...")
    expanded = expand_keywords_batch(raw_keywords)

    print("📊 Generating fake trend data...")
    provider = FakeProvider(expanded)
    enriched_data = provider.generate_fake_output()

    print("🧠 Analyzing trends...")
    analyzer = TrendAnalyzer()
    analysis_results = analyzer.analyze(enriched_data)

    print("⚠️ Extracting meaningful alerts...")
    alerts = extract_alerts_from_analysis(
        analysis_results,
        min_increase_pct=args.min_increase,
        max_decrease_pct=args.max_decrease
    )

    print("📤 Dispatching to Slack...")
    send_alerts_to_slack(alerts, dry_run=args.dry_run)

    print("✅ Done.")

if __name__ == "__main__":
    main()
