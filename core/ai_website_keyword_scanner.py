import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging at the top of the main script
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Add the project root to the system path to ensure imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the core components
from core.web_scraper import WebScraper
from core.ai_keyword_extractor import extract_keywords_from_scraped_text, categorize_keywords_with_ai
# Import the GoogleAdsProvider to use the new lightweight filtering method
from core.data_provider.google_ads_provider import GoogleAdsProvider


def scan_website_for_keywords(
        start_url: str,
        existing_structure: List[Dict[str, Any]],
        depth: int = 1,
        max_pages: int = 20,
        max_keywords: int = 100,
        language_code: str = "1000",
        geo_target_id: str = "2840",
        headlines_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Orchestrates the entire process of crawling a website, extracting keywords,
    filtering out low-quality keywords using a Google Ads API check, and then
    categorizing the clean list using AI. The output is formatted specifically
    for the UI's merge function.

    Args:
        start_url (str): The starting URL for the web crawl.
        existing_structure (List[Dict[str, Any]]): The current list of categories
                                                    and ad groups to merge new keywords into.
        depth (int): The number of link levels to crawl from the start_url.
        max_pages (int): The maximum number of unique pages to crawl.
        max_keywords (int): The maximum number of keywords to return.
        language_code (str): Google Ads language ID for filtering.
        geo_target_id (str): Google Ads geo target ID for filtering.
        headlines_only (bool): If True, restricts the source text for keyword extraction
                          to only text contained within HTML header tags (h1-h6).

    Returns:
        List[Dict[str, Any]]: The formatted data structure ready for merging,
                              in the format: [{'categories': [...]}]
    """

    start_url = start_url.strip()

    logging.info("🤖 Starting AI-powered keyword scan...")
    logging.info(f"URL: {start_url}, Depth: {depth}, Max Pages: {max_pages}, Max Keywords: {max_keywords}")
    logging.info(f"Filter settings: Language={language_code}, Geo={geo_target_id}, Headlines Only: {headlines_only}")

    # Step 1: Initialize and run the web scraper with max_pages limit
    scraper = WebScraper()
    try:
        # PASS THE NEW 'headlines' PARAMETER TO THE SCRAPER
        consolidated_text = scraper.scrape_website(start_url, depth, max_pages, headlines_only=headlines_only)
        print(consolidated_text)
        if not consolidated_text:
            logging.error("❌ Scraping returned no text. Cannot proceed.")
            return []
    except Exception as e:
        logging.error(f"❌ An error occurred during scraping: {e}", exc_info=True)
        return []

    logging.info(f"✅ Scraping complete. Total text size: {len(consolidated_text)} characters.")

    # Step 2: Use the AI to extract a raw list of keywords from the scraped text
    try:
        suggested_keywords_raw = extract_keywords_from_scraped_text(consolidated_text, max_keywords)
        if not suggested_keywords_raw:
            logging.warning("⚠️ AI extraction found no relevant keywords.")
            return []
    except Exception as e:
        logging.error(f"❌ An error occurred during AI extraction: {e}", exc_info=True)
        return []

    logging.info(f"✅ Raw keyword extraction complete. Found {len(suggested_keywords_raw)} unique keywords.")

    # Step 2.5: Lightweight Keyword Quality Filtering using Google Ads API
    try:
        # Initialize provider (data=None is fine for the filter method)
        google_ads_provider = GoogleAdsProvider(
            data=[],
            language_code=language_code,
            geo_target_id=geo_target_id
        )

        # Filter the raw list
        suggested_keywords_filtered = google_ads_provider.filter_keywords_by_monthly_volume(
            suggested_keywords_raw
        )

        keywords_removed = len(suggested_keywords_raw) - len(suggested_keywords_filtered)

        if keywords_removed > 0:
            logging.info(f"🧹 Filter removed {keywords_removed} low-volume/invalid keywords.")

        if not suggested_keywords_filtered:
            logging.warning("⚠️ All keywords were filtered out by the volume check. Cannot proceed to categorization.")
            return []

    except Exception as e:
        # Log the error but proceed with the raw list if filtering fails (safer than crashing)
        logging.error(
            f"⚠️ Failed to perform Google Ads keyword filtering. Proceeding with {len(suggested_keywords_raw)} raw keywords. Error: {e}",
            exc_info=True)
        suggested_keywords_filtered = suggested_keywords_raw

    # Step 3: Use the AI to categorize the clean list of keywords into the structured format
    try:
        # Prepare the existing structure for the AI (ensure keywords are a list of strings)
        new_existing_structure = existing_structure
        for category in new_existing_structure:
            for ad_group in category.get('ad_groups', []):
                # Ensure the 'keywords' field is handled correctly before passing to the AI
                if type(ad_group.get('keywords')) is not list:
                    # Assuming keywords might be a comma/newline separated string if stored oddly
                    keywords_list = ad_group.get('keywords', '').split("\n")
                    ad_group['keywords'] = [k.strip() for k in keywords_list if k.strip()]

        # Pass the FILTERED list to the AI
        categorized_structure = categorize_keywords_with_ai(suggested_keywords_filtered, new_existing_structure)

    except Exception as e:
        logging.error(f"❌ An error occurred during AI categorization: {e}", exc_info=True)
        return []

    logging.info("✅ AI categorization complete. Reformatting output for UI merge.")

    return categorized_structure


# This block allows you to run the file directly for testing the full pipeline.
if __name__ == "__main__":
    test_url = "https://www.apple.com/iphone/"
    test_depth = 1
    test_max_pages = 5
    test_max_keywords = 25

    # We need to simulate an existing structure for testing
    test_existing_structure = [
        {
            "category_name": "Outdoors & Garden",
            "ad_groups": [
                {
                    "ad_group_name": "Birds",
                    "keywords": ["pro automatic bird feeder"]
                }
            ]
        }
    ]

    logging.info("\n--- Running End-to-End Keyword Scanner Demo ---")

    # DEMO 1: Full Content Scan
    logging.info("\n--- DEMO 1: FULL CONTENT SCAN ---")
    final_structured_keywords_full = scan_website_for_keywords(
        test_url,
        test_existing_structure,
        test_depth,
        test_max_pages,
        test_max_keywords,
        headlines_only=False  # Full Content
    )
    print(json.dumps(final_structured_keywords_full, indent=2))

    logging.info("\n--- DEMO 2: HEADLINES ONLY SCAN ---")
    # DEMO 2: Headlines Only Scan
    final_structured_keywords_headlines = scan_website_for_keywords(
        test_url,
        test_existing_structure,
        test_depth,
        test_max_pages,
        test_max_keywords,
        headlines_only=True  # Headlines Only
    )
    print(json.dumps(final_structured_keywords_headlines, indent=2))