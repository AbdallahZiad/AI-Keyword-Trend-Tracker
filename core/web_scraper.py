import requests
from bs4 import BeautifulSoup
from collections import deque
import time
import random
from urllib.parse import urljoin, urlparse
from typing import Set, Deque, Dict, Any, Union

# Import Python's built-in logging module
import logging

# Configure logging for the module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WebScraper:
    """
    A robust web scraper for crawling websites up to a specified depth and
    extracting clean text content.
    """

    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.crawled_pages_count = 0

    def _fetch_page_content(self, url: str) -> Union[str, None]:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        }
        max_retries = 3
        base_delay_seconds = 2

        for retry_count in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching {url}: {e}")
                if retry_count < max_retries - 1:
                    sleep_time = (base_delay_seconds * (2 ** retry_count)) + random.uniform(0, 1)
                    logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logging.error(f"Max retries reached for {url}. Skipping.")
                    return None
        return None

    def _extract_text_and_links(self, html_content: str, base_url: str) -> tuple[str, list[str]]:
        if not html_content:
            return "", []

        soup = BeautifulSoup(html_content, 'html.parser')

        for script_or_style in soup(['script', 'style', 'noscript']):
            script_or_style.decompose()

        # Find the main content of the page, with fallback options.
        main_content = (
                soup.find('main')
                or soup.find('article')
                or soup.find(id='content')
                or soup.find(class_='main-content')
                or soup.find('body')
        )

        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            text = ' '.join(text.split())
        else:
            text = ""

        links = []
        parsed_base_url = urlparse(base_url)

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()

            if not href or href.startswith(("javascript:", "mailto:", "#")):
                continue

            full_url = urljoin(base_url, href)
            parsed_full_url = urlparse(full_url)

            if parsed_full_url.scheme in ['http', 'https'] and parsed_full_url.netloc == parsed_base_url.netloc:
                # Normalize the URL by removing fragment and trailing slash
                clean_url = parsed_full_url._replace(fragment="").geturl().rstrip('/')

                # Check if URL is not already visited
                if clean_url not in self.visited_urls:
                    links.append(clean_url)

        # The subsequent link deduplication is now unnecessary and removed.
        return text, links

    def scrape_website(self, start_url: str, depth: int, max_pages: int) -> str:
        url_queue: Deque[tuple[str, int]] = deque([(start_url, 0)])
        all_text = []

        while url_queue and self.crawled_pages_count < max_pages:
            current_url, current_depth = url_queue.popleft()

            if current_url in self.visited_urls:
                continue

            # Increment the page count and check the limit
            self.crawled_pages_count += 1
            if self.crawled_pages_count > max_pages:
                break

            self.visited_urls.add(current_url)

            logging.info(f"Crawling: {current_url} (Depth: {current_depth})")

            html_content = self._fetch_page_content(current_url)
            if not html_content:
                continue

            text, links = self._extract_text_and_links(html_content, current_url)
            if text:
                all_text.append(text)

            if current_depth < depth:
                for link in links:
                    if link not in self.visited_urls:
                        url_queue.append((link, current_depth + 1))

        logging.info(f"Scraping complete. Visited {len(self.visited_urls)} unique pages.")
        return " ".join(all_text)