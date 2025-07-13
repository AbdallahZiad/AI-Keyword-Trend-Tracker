import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import KeywordDataProvider


class FakeProvider(KeywordDataProvider):
    def __init__(
        self,
        data: List[Dict[str, Any]],
        month_index: Optional[int] = None,
        manual_trend_boosts: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.data = data
        self.month_index = month_index if month_index is not None else datetime.now().month - 1
        self.boosts = manual_trend_boosts or {}

    def get_monthly_volumes_by_year(self, keyword: str) -> Dict[int, List[int]]:
        current_year = datetime.now().year
        current_month = datetime.now().month
        start_year = current_year - 3
        volumes = {}

        # Step 1: generate random data
        for year in range(start_year, current_year + 1):
            if year == current_year:
                months = [random.randint(0, 150) for _ in range(current_month)]
                months.extend([0] * (12 - current_month))
            else:
                months = [random.randint(0, 150) for _ in range(12)]
            volumes[year] = months

        # Step 2: apply boosts if needed
        if keyword in self.boosts:
            boost_info = self.boosts[keyword]
            if "1mo" in boost_info:
                self._apply_1mo_boost(volumes, boost_info["1mo"])
            elif "3mo" in boost_info:
                self._apply_3mo_boost(volumes, boost_info["3mo"])

        return volumes

    def _apply_1mo_boost(self, volumes: Dict[int, List[int]], boost: float):
        """
        Ensures that last year's next month is `boost`% higher than the same year's current month.
        """
        years = sorted(volumes.keys())
        last_year = years[-2]  # current year is last element
        i = self.month_index
        j = i + 1

        if j >= 12:
            return  # can't go beyond December

        base = volumes[last_year][i]
        if base == 0:
            base = random.randint(10, 100)
            volumes[last_year][i] = base

        volumes[last_year][j] = int(base * (1 + boost))

    def _apply_3mo_boost(self, volumes: Dict[int, List[int]], boost: float):
        """
        Ensures that next 3 months average in each of the last 3 years
        is `boost`% higher than that same year's current month.
        """
        years = sorted(volumes.keys())[:-1]  # exclude current year
        i = self.month_index
        j_range = [i + 1, i + 2, i + 3]

        if max(j_range) >= 12:
            return  # would overflow months

        for year in years:
            base = volumes[year][i]
            if base == 0:
                base = random.randint(10, 100)
                volumes[year][i] = base

            target_avg = base * (1 + boost)

            for j in j_range:
                # Add a bit of variance while keeping average close to target
                fluctuation = random.uniform(-0.1, 0.1)
                volumes[year][j] = int(target_avg * (1 + fluctuation))

    def generate_fake_output(self) -> List[Dict[str, Any]]:
        output = []

        for entry in self.data:
            keyword = entry["keyword"]
            similar_keywords = entry.get("similar_keywords", [])

            keyword_trend = self.get_monthly_volumes_by_year(keyword)
            similar_trends = {
                kw: self.get_monthly_volumes_by_year(kw)
                for kw in similar_keywords
            }

            output.append({
                "keyword": keyword,
                "trend_history": keyword_trend,
                "similar_keywords": similar_trends
            })

        return output
