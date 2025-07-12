from abc import ABC, abstractmethod
from typing import Dict, List

class KeywordDataProvider(ABC):
    @abstractmethod
    def get_monthly_volumes_by_year(self, keyword: str) -> Dict[int, List[int]]:
        """
        Returns monthly search volumes per year.
        Format:
        {
            2022: [Jan, Feb, ..., Dec],
            2023: [...],
            2024: [...],
            2025: [up to current month]
        }
        """
