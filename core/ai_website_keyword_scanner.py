import sys
import os
import json
import logging
from pathlib import Path
from typing import List

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
from core.ai_keyword_extractor import extract_keywords_from_scraped_text

def scan_website_for_keywords(start_url: str, depth: int = 1, max_pages: int = 20, max_keywords: int = 100) -> List[str]:
    """
    Orchestrates the entire process of crawling a website and extracting keywords
    using AI.

    Args:
        start_url (str): The starting URL for the web crawl.
        depth (int): The number of link levels to crawl from the start_url.
        max_pages (int): The maximum number of unique pages to crawl.
        max_keywords (int): The maximum number of keywords to return.

    Returns:
        List[str]: A deduplicated list of AI-suggested keywords.
    """
    logging.info("🤖 Starting AI-powered keyword scan...")
    logging.info(f"URL: {start_url}, Depth: {depth}, Max Pages: {max_pages}, Max Keywords: {max_keywords}")

    # Step 1: Initialize and run the web scraper with max_pages limit
    scraper = WebScraper()
    try:
        consolidated_text = scraper.scrape_website(start_url, depth, max_pages)
        if not consolidated_text:
            logging.error("❌ Scraping returned no text. Cannot proceed with keyword extraction.")
            return []
    except Exception as e:
        logging.error(f"❌ An error occurred during scraping: {e}")
        return []

    logging.info(f"✅ Scraping complete. Total text size: {len(consolidated_text)} characters.")

    # Step 2: Use the AI to extract keywords from the scraped text with max_keywords limit
    try:
        suggested_keywords = extract_keywords_from_scraped_text(consolidated_text, max_keywords)
    except Exception as e:
        logging.error(f"❌ An error occurred during AI keyword extraction: {e}")
        return []

    logging.info("✅ AI keyword extraction complete.")
    logging.info(f"Found {len(suggested_keywords)} unique keywords.")

    return suggested_keywords


# This block allows you to run the file directly for testing the full pipeline.
if __name__ == "__main__":
    test_url = "https://www.4iq.lt/"
    test_depth = 1
    test_max_pages = 5
    test_max_keywords = 10

    logging.info("\n--- Running End-to-End Keyword Scanner Demo ---")

    final_keywords = scan_website_for_keywords(test_url, test_depth, test_max_pages, test_max_keywords)

    if final_keywords:
        logging.info("\n🎉 Final AI-Suggested Keywords:")
        logging.info(json.dumps(final_keywords, indent=2, ensure_ascii=False))
        logging.info(f"\nTotal keywords found: {len(final_keywords)}")
    else:
        logging.info("\nNo keywords were generated.")