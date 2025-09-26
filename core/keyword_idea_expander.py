import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to sys.path to access modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data_provider.google_ads_provider import GoogleAdsProvider


class KeywordIdeaExpander:
    """
    Expands ad group keyword lists by using the Google Ads API to generate
    relevant keyword ideas based on existing keywords or the ad group's name.
    """

    def __init__(self, google_ads_provider: GoogleAdsProvider, keywords_per_group: int = 5):
        self.provider = google_ads_provider
        self.keywords_per_group = keywords_per_group

    def expand_keywords(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a nested data structure of categories and ad groups, and populates
        each ad group with a target number of keywords.

        Args:
            data: A list of categories, each containing ad groups. Ad groups
                  may or may not contain initial keywords.

        Returns:
            The same data structure with ad groups now populated with up to
            `keywords_per_group` keywords.
        """
        for category in data:
            for ad_group in category.get("ad_groups", []):
                existing_keywords = [kw.get('keyword') for kw in ad_group.get("keywords", []) if kw.get('keyword')]
                num_existing = len(existing_keywords)

                # If the ad group already has enough keywords, skip
                if num_existing >= self.keywords_per_group:
                    print(f"Ad group '{ad_group.get('ad_group')}' already has enough keywords. Skipping expansion.")
                    continue

                # Determine the seeds for keyword idea generation
                seeds = existing_keywords
                if not seeds:
                    # If there are no existing keywords, use the ad group name as the seed
                    ad_group_name = ad_group.get("ad_group")
                    if ad_group_name:
                        seeds = [ad_group_name]
                    else:
                        print(f"Skipping ad group with no name or keywords.")
                        continue

                print(f"Expanding ad group '{ad_group.get('ad_group')}' with seeds: {seeds}...")

                # Request more keywords than needed to allow for filtering
                keywords_to_fetch = self.keywords_per_group - num_existing + 5  # Fetch a few extra

                # Call the provider to get keyword ideas
                new_ideas = self.provider.get_keyword_ideas(
                    seed_keywords=seeds,
                    max_results=keywords_to_fetch
                )

                # Filter out duplicates and append to the existing list
                unique_new_keywords = [
                    {"keyword": kw} for kw in new_ideas if kw not in existing_keywords
                ]

                # Combine existing keywords with new ideas, respecting the limit
                current_keywords_count = num_existing
                for new_kw_dict in unique_new_keywords:
                    if current_keywords_count < self.keywords_per_group:
                        ad_group["keywords"].append(new_kw_dict)
                        current_keywords_count += 1
                    else:
                        break

                print(f"  -> Final keyword count for '{ad_group.get('ad_group')}': {len(ad_group['keywords'])}")

        return data