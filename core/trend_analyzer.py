import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TrendAnalyzer:
    def __init__(self, month_index: Optional[int] = None):
        """
        Initializes the TrendAnalyzer with the current month and future month indices.
        """
        # The month index is always the previous month to the current one
        # to ensure we don't use the current month's zero data.
        self.month_index = month_index if month_index is not None else (datetime.now().month - 2 + 12) % 12
        self.next_month_index = (self.month_index + 1) % 12
        self.next_3mo_indices = [(self.month_index + i) % 12 for i in range(1, 4)]
        self.current_year = datetime.now().year
        self.previous_month_current_year = (datetime.now().month - 1 + 12) % 12

    def _safe_get(self, arr: List[int], i: int) -> int:
        """Safely gets a value from a list, returning 0 if the index is out of bounds."""
        return arr[i] if i < len(arr) else 0

    def _safe_avg(self, arr: List[int], idxs: List[int]) -> float:
        """Calculates the average of values at specified indices, handling empty lists."""
        vals = [self._safe_get(arr, i) for i in idxs]
        non_zero_vals = [v for v in vals if v > 0]
        return sum(non_zero_vals) / len(non_zero_vals) if non_zero_vals else 0

    def _calculate_pct_change(self, history: Dict[int, List[int]], single_month: bool) -> float:
        """
        Calculates the average percentage change based on historical data.
        """
        changes = []
        current_year = datetime.now().year

        for year_str, months in history.items():
            try:
                year = int(year_str)
            except ValueError:
                continue

            if year >= current_year:
                continue

            current_value = self._safe_get(months, self.month_index)
            if current_value == 0:
                continue

            if single_month:
                future_value = self._safe_get(months, self.next_month_index)
            else:
                future_value = self._safe_avg(months, self.next_3mo_indices)

            if future_value > 0:
                change = (future_value - current_value) / current_value
                changes.append(change)

        if not changes:
            return 0.0

        return round(sum(changes) / len(changes) * 100, 1)

    def _calculate_avg_monthly_searches(self, history: Dict[int, List[int]]) -> int:
        """
        Calculates the average monthly searches for all available data up to the previous month of the current year.
        """
        all_searches = []
        for year_str, months in history.items():
            try:
                year = int(year_str)
            except ValueError:
                continue

            if year < self.current_year:
                all_searches.extend(months)
            elif year == self.current_year:
                # Add data up to the previous month
                all_searches.extend(months[:self.previous_month_current_year])

        if not all_searches:
            return 0

        # Filter out zero values which might represent missing data
        valid_searches = [s for s in all_searches if s > 0]
        return int(np.mean(valid_searches)) if valid_searches else 0

    def _calculate_seasonal_volatility(self, history: Dict[int, List[int]]) -> float:
        """
        Calculates the seasonal volatility score by measuring the standard deviation
        of a keyword's monthly search volumes relative to its mean.
        """
        monthly_searches = {}
        for year_str, months in history.items():
            try:
                year = int(year_str)
            except ValueError:
                continue

            if year < self.current_year:
                for i, searches in enumerate(months):
                    if searches > 0:
                        monthly_searches.setdefault(i, []).append(searches)

        # Calculate mean for each month across all years
        monthly_means = [np.mean(monthly_searches.get(i, [0])) for i in range(12)]

        if np.sum(monthly_means) == 0:
            return 0.0

        # Calculate standard deviation of monthly means
        std_dev = np.std(monthly_means)

        # Normalize the standard deviation by the mean of all monthly means
        avg_monthly_mean = np.mean(monthly_means)

        if avg_monthly_mean == 0:
            return 0.0

        return round(std_dev / avg_monthly_mean, 2)

    def _analyze_keyword(self, keyword_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes a single keyword's trend based on its history, adding new metrics.
        """
        history = keyword_data.get("trend_history", {})

        # Calculate new metrics
        avg_monthly_searches = self._calculate_avg_monthly_searches(history)
        seasonal_volatility_score = self._calculate_seasonal_volatility(history)

        # Retain existing metrics
        pct_change_next_month = self._calculate_pct_change(history, single_month=True)
        pct_change_next_3mo = self._calculate_pct_change(history, single_month=False)

        # Combine all metrics into the output
        keyword_data.update({
            "avg_monthly_searches": avg_monthly_searches,
            "seasonal_volatility_score": seasonal_volatility_score,
            "pct_change_next_month": pct_change_next_month,
            "pct_change_next_3mo": pct_change_next_3mo,
        })
        return keyword_data

    def _analyze_ad_group(self, ad_group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes an ad group by aggregating insights from its keywords.
        """
        analyzed_keywords = [self._analyze_keyword(kw) for kw in ad_group_data.get("keywords", [])]
        ad_group_data["keywords"] = analyzed_keywords

        if not analyzed_keywords:
            return ad_group_data

        # Calculate the average of keyword forecasts, preserving other data
        avg_pct_change_next_month = sum(kw['pct_change_next_month'] for kw in analyzed_keywords) / len(
            analyzed_keywords)
        avg_pct_change_next_3mo = sum(kw['pct_change_next_3mo'] for kw in analyzed_keywords) / len(analyzed_keywords)

        # Add the new ad group-level metrics
        avg_monthly_searches = sum(kw['avg_monthly_searches'] for kw in analyzed_keywords) / len(analyzed_keywords)
        seasonal_volatility_score = sum(kw['seasonal_volatility_score'] for kw in analyzed_keywords) / len(
            analyzed_keywords)

        ad_group_data.update({
            "pct_change_next_month": round(avg_pct_change_next_month, 1),
            "pct_change_next_3mo": round(avg_pct_change_next_3mo, 1),
            "avg_monthly_searches": int(avg_monthly_searches),
            "seasonal_volatility_score": round(seasonal_volatility_score, 2),
        })

        return ad_group_data

    def _analyze_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes a category by aggregating insights from its ad groups.
        """
        analyzed_ad_groups = [self._analyze_ad_group(group) for group in category_data.get("ad_groups", [])]
        category_data["ad_groups"] = analyzed_ad_groups

        if not analyzed_ad_groups:
            return category_data

        # Calculate the average of ad group forecasts, preserving other data
        avg_pct_change_next_month = sum(group['pct_change_next_month'] for group in analyzed_ad_groups) / len(
            analyzed_ad_groups)
        avg_pct_change_next_3mo = sum(group['pct_change_next_3mo'] for group in analyzed_ad_groups) / len(
            analyzed_ad_groups)

        # Add the new category-level metrics
        avg_monthly_searches = sum(group['avg_monthly_searches'] for group in analyzed_ad_groups) / len(
            analyzed_ad_groups)
        seasonal_volatility_score = sum(group['seasonal_volatility_score'] for group in analyzed_ad_groups) / len(
            analyzed_ad_groups)

        category_data.update({
            "pct_change_next_month": round(avg_pct_change_next_month, 1),
            "pct_change_next_3mo": round(avg_pct_change_next_3mo, 1),
            "avg_monthly_searches": int(avg_monthly_searches),
            "seasonal_volatility_score": round(seasonal_volatility_score, 2),
        })

        return category_data

    def analyze(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        The main public method to orchestrate the analysis for a list of categories.
        Input: a list of categories, each containing ad groups and keywords.
        Output: a list of categories with analyzed trend data at each level.
        """
        if not data:
            return []

        analyzed_results = [self._analyze_category(category_data) for category_data in data]
        return analyzed_results