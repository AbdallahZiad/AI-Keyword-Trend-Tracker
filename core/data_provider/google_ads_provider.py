import os
import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Add the project root to sys.path to access settings
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .base import KeywordDataProvider
from config import settings

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core.exceptions import ResourceExhausted


class GoogleAdsProvider(KeywordDataProvider):
    """
    A data provider that fetches real keyword trend data from the Google Ads API.
    """

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.client = self._get_google_ads_client()
        self.keyword_plan_service = self.client.get_service("KeywordPlanIdeaService")
        self.customer_id = settings.GOOGLE_CUSTOMER_ID

    def _get_google_ads_client(self) -> GoogleAdsClient:
        """
        Initializes and returns a GoogleAdsClient instance using environment variables,
        with an explicit setting for use_proto_plus.
        """
        try:
            config = {
                "developer_token": settings.GOOGLE_DEVELOPER_TOKEN,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": settings.GOOGLE_REFRESH_TOKEN,
                "login_customer_id": settings.GOOGLE_LOGIN_CUSTOMER_ID,
                "use_proto_plus": True
            }
            return GoogleAdsClient.load_from_dict(config)
        except GoogleAdsException as e:
            print(f"Error initializing Google Ads client: {e}")
            raise

    def _retry_on_rate_limit(self, func, *args, **kwargs):
        """
        A simple retry mechanism with exponential backoff for rate-limiting errors.
        This handles the specific RESOURCE_EXHAUSTED error code from the API.
        """
        max_retries = 5
        base_delay_seconds = 4
        retry_count = 0
        last_exception = None

        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except GoogleAdsException as ex:
                last_exception = ex
                is_rate_limit_error = False
                for error in ex.failure.errors:
                    if error.error_code.HasField("quota_error") and \
                            error.error_code.quota_error == self.client.enums.QuotaErrorEnum.RESOURCE_TEMPORARILY_EXHAUSTED:
                        is_rate_limit_error = True
                        break

                if is_rate_limit_error:
                    sleep_time = (base_delay_seconds * (2 ** retry_count)) + random.uniform(0, 1)
                    print(
                        f"Encountered a rate-limit error. Retrying in {sleep_time:.2f} seconds... "
                        f"(Attempt {retry_count + 1}/{max_retries})"
                    )
                    time.sleep(sleep_time)
                    retry_count += 1
                else:
                    # Not a rate-limit error, re-raise the exception
                    raise
            except ResourceExhausted as ex:
                last_exception = ex
                sleep_time = (base_delay_seconds * (2 ** retry_count)) + random.uniform(0, 1)
                print(
                    f"Encountered a gRPC ResourceExhausted error. Retrying in {sleep_time:.2f} seconds... "
                    f"(Attempt {retry_count + 1}/{max_retries})"
                )
                time.sleep(sleep_time)
                retry_count += 1

        # If all retries fail, raise the last exception
        if last_exception:
            raise last_exception
        else:
            # Should not be reachable, but as a fallback
            raise Exception("Retry mechanism failed without catching an exception.")

    def get_monthly_volumes_by_year(self, keyword: str) -> Dict[int, List[int]]:
        """
        Fetches historical monthly search volume for a single keyword and formats it.
        """
        request = self.client.get_type("GenerateKeywordHistoricalMetricsRequest")
        request.customer_id = self.customer_id
        request.keywords = [keyword]

        # Use a dictionary to map month enums to 0-based indices for robustness
        month_to_index = {
            self.client.enums.MonthOfYearEnum.JANUARY: 0,
            self.client.enums.MonthOfYearEnum.FEBRUARY: 1,
            self.client.enums.MonthOfYearEnum.MARCH: 2,
            self.client.enums.MonthOfYearEnum.APRIL: 3,
            self.client.enums.MonthOfYearEnum.MAY: 4,
            self.client.enums.MonthOfYearEnum.JUNE: 5,
            self.client.enums.MonthOfYearEnum.JULY: 6,
            self.client.enums.MonthOfYearEnum.AUGUST: 7,
            self.client.enums.MonthOfYearEnum.SEPTEMBER: 8,
            self.client.enums.MonthOfYearEnum.OCTOBER: 9,
            self.client.enums.MonthOfYearEnum.NOVEMBER: 10,
            self.client.enums.MonthOfYearEnum.DECEMBER: 11,
        }

        request.language = "languageConstants/1000"
        request.geo_target_constants.append("geoTargetConstants/2840")

        historical_metrics_options = self.client.get_type("HistoricalMetricsOptions")

        today = datetime.now()
        end_date = today.replace(day=1)
        start_date = end_date - relativedelta(months=42)

        historical_metrics_options.year_month_range.start.year = start_date.year
        historical_metrics_options.year_month_range.start.month = start_date.month
        historical_metrics_options.year_month_range.end.year = end_date.year
        historical_metrics_options.year_month_range.end.month = end_date.month

        request.historical_metrics_options = historical_metrics_options

        try:
            response = self._retry_on_rate_limit(
                self.keyword_plan_service.generate_keyword_historical_metrics,
                request=request
            )

            if not response.results or not response.results[0].keyword_metrics.monthly_search_volumes:
                return {}

            trend_data = {}
            for monthly_search_volume in response.results[0].keyword_metrics.monthly_search_volumes:
                year = monthly_search_volume.year
                month_enum = monthly_search_volume.month
                search_volume = monthly_search_volume.monthly_searches or 0

                month_index = month_to_index.get(month_enum)

                if month_index is not None:
                    if year not in trend_data:
                        trend_data[year] = [0] * 12
                    trend_data[year][month_index] = search_volume
                else:
                    print(f"Skipping invalid month enum '{month_enum}' for keyword '{keyword}' in year '{year}'.")

            # Sort the years for a clean output
            sorted_trend_data = {int(year): trend_data[year] for year in sorted(trend_data)}
            return sorted_trend_data

        except GoogleAdsException as ex:
            print(f"Request with ID '{ex.request_id}' failed.")
            for error in ex.failure.errors:
                print(f"\tError code: {error.error_code}")
                print(f"\tMessage: {error.message}")
            return {}

    def generate_output(self) -> List[Dict[str, Any]]:
        """
        Generates the final output by fetching real keyword trend data from the API
        and structuring it according to the required format.
        """
        output = []
        for entry in self.data:
            keyword = entry["keyword"]
            similar_keywords = entry.get("similar_keywords", [])

            keyword_trend = self.get_monthly_volumes_by_year(keyword)

            similar_trends = {}
            for similar_kw in similar_keywords:
                similar_trends[similar_kw] = self.get_monthly_volumes_by_year(similar_kw)

            output.append({
                "keyword": keyword,
                "trend_history": keyword_trend,
                "similar_keywords": similar_trends
            })
        return output