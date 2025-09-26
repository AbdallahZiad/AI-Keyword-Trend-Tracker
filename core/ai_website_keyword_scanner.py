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

def scan_website_for_keywords(
        start_url: str,
        existing_structure: List[Dict[str, Any]],
        depth: int = 1,
        max_pages: int = 20,
        max_keywords: int = 100
) -> List[Dict[str, Any]]:
    """
    Orchestrates the entire process of crawling a website, extracting keywords,
    and then categorizing them using AI. The output is formatted specifically
    for the UI's merge function.

    Args:
        start_url (str): The starting URL for the web crawl.
        existing_structure (List[Dict[str, Any]]): The current list of categories
                                                    and ad groups to merge new keywords into.
        depth (int): The number of link levels to crawl from the start_url.
        max_pages (int): The maximum number of unique pages to crawl.
        max_keywords (int): The maximum number of keywords to return.

    Returns:
        List[Dict[str, Any]]: The formatted data structure ready for merging,
                              in the format: [{'categories': [...]}]
    """

    start_url = start_url.strip()

    logging.info("🤖 Starting AI-powered keyword scan...")
    logging.info(f"URL: {start_url}, Depth: {depth}, Max Pages: {max_pages}, Max Keywords: {max_keywords}")

    # Step 1: Initialize and run the web scraper with max_pages limit
    scraper = WebScraper()
    try:
        consolidated_text = scraper.scrape_website(start_url, depth, max_pages)
        if not consolidated_text:
            logging.error("❌ Scraping returned no text. Cannot proceed.")
            return []
    except Exception as e:
        logging.error(f"❌ An error occurred during AI categorization: {e}", exc_info=True)
        return []

    logging.info(f"✅ Scraping complete. Total text size: {len(consolidated_text)} characters.")

    # Step 2: Use the AI to extract a raw list of keywords from the scraped text
    try:
        suggested_keywords = extract_keywords_from_scraped_text(consolidated_text, max_keywords)
        if not suggested_keywords:
            logging.warning("⚠️ AI extraction found no relevant keywords.")
            return []
    except Exception as e:
        logging.error(f"❌ An error occurred during AI categorization: {e}", exc_info=True)
        return []

    logging.info(f"✅ Raw keyword extraction complete. Found {len(suggested_keywords)} unique keywords.")

    # Step 3: Use the AI to categorize the raw keywords into the structured format
    try:
        # This returns a List[Dict[str, Any]] of categories
        new_existing_structure = existing_structure
        for category in new_existing_structure:
            for ad_group in category['ad_groups']:
                if type(ad_group['keywords']) is not list:
                    ad_group['keywords'] = ad_group.get('keywords', '').split("\n")
        categorized_structure = categorize_keywords_with_ai(suggested_keywords, new_existing_structure)
    except Exception as e:
        logging.error(f"❌ An error occurred during AI categorization: {e}", exc_info=True)
        return []

    logging.info("✅ AI categorization complete. Reformatting output for UI merge.")

    return categorized_structure


# This block allows you to run the file directly for testing the full pipeline.
if __name__ == "__main__":
    test_url = "https://webscraper.io/test-sites/e-commerce/allinone"
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

    final_structured_keywords = scan_website_for_keywords(
        test_url,
        test_existing_structure,
        test_depth,
        test_max_pages,
        test_max_keywords
    )

    print(final_structured_keywords)