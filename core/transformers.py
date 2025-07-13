def extract_alerts_from_analysis(
    results: list[dict],
    min_increase_pct: float = 10.0,
    max_decrease_pct: float = -10.0
) -> list[dict]:
    alerts = []

    for entry in results:
        pct_change = entry["total_weighted"]["pct_change_month"]

        if pct_change >= min_increase_pct or pct_change <= max_decrease_pct:
            alert = {
                "keyword": entry["keyword"],
                "current": entry["current"],
                "expected_next_month": round(entry["expected_next_month"], 1),
                "expected_next_3mo_avg": round(entry["expected_next_3mo_avg"], 1),
                "pct_change_month": round(pct_change, 1),
                "pct_change_3mo": round(entry["total_weighted"]["pct_change_3mo"], 1)
            }
            alerts.append(alert)

    return alerts
