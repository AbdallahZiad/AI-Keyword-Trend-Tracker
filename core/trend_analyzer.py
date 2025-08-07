from typing import List, Dict, Any, Optional
from datetime import datetime


class TrendAnalyzer:
    def __init__(self, month_index: Optional[int] = None):
        self.month_index = month_index if month_index is not None else datetime.now().month - 1
        self.next_month_index = (self.month_index + 1) % 12
        self.next_3mo_indices = [(self.month_index + i) % 12 for i in range(1, 4)]

    def _average_change(self, history: Dict[int, List[int]], single_month: bool) -> float:
        changes = []

        # Exclude the current year from the analysis
        current_year = datetime.now().year
        historical_years = [year for year in history.keys() if year != current_year]

        if not historical_years:
            return 0.0

        for year in historical_years:
            months = history[year]
            current = self._safe_get(months, self.month_index)
            if current == 0:
                continue

            if single_month:
                future = self._safe_get(months, self.next_month_index)
                change = (future - current) / current
            else:
                future = self._safe_avg(months, self.next_3mo_indices)
                change = (future - current) / current

            changes.append(change)

        if not changes:
            return 0.0

        return round(sum(changes) / len(changes) * 100, 1)

    def analyze(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []

        for entry in data:
            keyword = entry["keyword"]
            history = entry["trend_history"]
            similar_map = entry.get("similar_keywords", {})

            pct_change_month = self._average_change(history, single_month=True)
            pct_change_3mo = self._average_change(history, single_month=False)

            similar_results = []
            if similar_map:
                for sim_kw, sim_hist in similar_map.items():
                    sim_pct_month = self._average_change(sim_hist, single_month=True)
                    sim_pct_3mo = self._average_change(sim_hist, single_month=False)

                    similar_results.append({
                        "keyword": sim_kw,
                        "pct_change_month": sim_pct_month,
                        "pct_change_3mo": sim_pct_3mo
                    })

            total_weighted = self._weighted_change(
                pct_change_month, pct_change_3mo, similar_results
            )

            results.append({
                "keyword": keyword,
                "pct_change_month": pct_change_month,
                "pct_change_3mo": pct_change_3mo,
                "similar_keywords": similar_results,
                "total_weighted": total_weighted
            })

        return results

    def _safe_get(self, arr: List[int], i: int) -> int:
        return arr[i] if i < len(arr) else 0

    def _safe_avg(self, arr: List[int], idxs: List[int]) -> float:
        vals = [arr[i] for i in idxs if i < len(arr)]
        return sum(vals) / len(vals) if vals else 0

    def _weighted_change(self, main_pct_month, main_pct_3mo, similar_list) -> Dict[str, float]:
        n = len(similar_list)
        if n == 0:
            return {
                "pct_change_month": main_pct_month,
                "pct_change_3mo": main_pct_3mo
            }

        sim_months = sum(s["pct_change_month"] for s in similar_list)
        sim_3mos = sum(s["pct_change_3mo"] for s in similar_list)

        weighted_month = round(0.5 * main_pct_month + 0.5 * sim_months / n, 1)
        weighted_3mo = round(0.5 * main_pct_3mo + 0.5 * sim_3mos / n, 1)

        return {
            "pct_change_month": weighted_month,
            "pct_change_3mo": weighted_3mo
        }