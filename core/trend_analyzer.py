from typing import List, Dict, Any, Optional


class TrendAnalyzer:
    def __init__(self, month_index: Optional[int] = None):
        from datetime import datetime
        self.month_index = self.month_index = month_index if month_index is not None else datetime.now().month - 1
        self.next_month_index = (self.month_index + 1) % 12
        self.next_3mo_indices = [(self.month_index + i) % 12 for i in range(1, 4)]

    def _average_change(self, history: Dict[int, List[int]], single_month: bool) -> float:
        changes = []

        for year in history:
            if year == max(history):  # Skip current year
                continue

            months = history[year]
            current = self._safe_get(months, self.month_index)
            if current == 0:
                continue  # skip to avoid div-by-zero

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

            # Collect changes across all past years
            pct_change_month = self._average_change(history, single_month=True)
            pct_change_3mo = self._average_change(history, single_month=False)

            # Get current month value from the most recent year for context
            last_year = max(history)
            current = history[last_year][self.month_index]
            expected_next_month = round(current * (1 + pct_change_month / 100), 1)
            expected_next_3mo = round(current * (1 + pct_change_3mo / 100), 1)

            similar_results = []
            for sim_kw, sim_hist in similar_map.items():
                sim_pct_month = self._average_change(sim_hist, single_month=True)
                sim_pct_3mo = self._average_change(sim_hist, single_month=False)

                sim_current = sim_hist[last_year][self.month_index]
                sim_next = round(sim_current * (1 + sim_pct_month / 100), 1)
                sim_avg = round(sim_current * (1 + sim_pct_3mo / 100), 1)

                similar_results.append({
                    "keyword": sim_kw,
                    "current": sim_current,
                    "expected_next_month": sim_next,
                    "expected_next_3mo_avg": sim_avg,
                    "pct_change_month": sim_pct_month,
                    "pct_change_3mo": sim_pct_3mo
                })

            total_weighted = self._weighted_change(
                pct_change_month, pct_change_3mo, similar_results
            )

            results.append({
                "keyword": keyword,
                "current": current,
                "expected_next_month": expected_next_month,
                "expected_next_3mo_avg": expected_next_3mo,
                "pct_change_month": pct_change_month,
                "pct_change_3mo": pct_change_3mo,
                "similar_keywords": similar_results,
                "total_weighted": total_weighted
            })

        return results

    def _safe_get(self, arr: List[int], i: int) -> float:
        return arr[i] if i < len(arr) else 0

    def _safe_avg(self, arr: List[int], idxs: range) -> float:
        vals = [arr[i] for i in idxs if i < len(arr)]
        return sum(vals) / len(vals) if vals else 0

    def _pct_change(self, current: float, next_val: float) -> float:
        if current == 0:
            return 0
        return round(((next_val - current) / current) * 100, 1)

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
