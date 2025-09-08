import sys
import os
import json
import re
import logging
from pathlib import Path
from typing import List
from openai import OpenAI
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

MAX_PROMPT_TOKENS = 3000
CHARS_PER_TOKEN = 4
MAX_CHUNK_SIZE = MAX_PROMPT_TOKENS * CHARS_PER_TOKEN


def _split_text_into_chunks(text: str) -> List[str]:
    if not text:
        return []
    chunks = []
    current_chunk = ""
    segments = re.split(r'(?<=[.?!])\s+', text)
    for segment in segments:
        if len(current_chunk) + len(segment) + 1 > MAX_CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = segment
        else:
            current_chunk += (" " + segment) if current_chunk else segment
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def _extract_keywords_from_chunk(
        text_chunk: str,
        model: str = "gpt-3.5-turbo"
) -> List[str]:
    if not text_chunk or len(text_chunk) < 100:
        return []

    prompt = (
        "You are a skilled and experienced search marketing analyst. "
        "Your task is to analyze the following web page content and identify a list of "
        "highly relevant and commercially valuable keywords, focusing on topics and entities mentioned in the text.\n\n"
        "The keywords should be:\n"
        "- Directly related to the products, services, or topics discussed.\n"
        "- Phrases that a potential customer would use in a search engine.\n"
        "- A mix of short-tail and long-tail keywords.\n"
        "- Do not include generic words or adjectives. Only keywords that you think some business would want to track!\n"
        "For example, do not include something like 'Recommended'\n"
        "Also, the data you get is from a website dump, make sure not accidentally add website elements like the keyword 'filter'\n"
        "- Return ONLY a single, valid Python list of strings. Do not include any explanations, "
        "introductory text, or concluding remarks outside of the list.\n\n"
        "Text to analyze:\n"
        "--- START OF TEXT ---\n"
        f"{text_chunk}\n"
        "--- END OF TEXT ---\n\n"
        "Generate a list of keywords:"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=512,
        )
        raw_response = response.choices[0].message.content.strip()

        if not raw_response.startswith('[') or not raw_response.endswith(']'):
            logging.warning(f"Response does not start/end with brackets. Raw: {raw_response[:50]}...")
            match = re.search(r'\[(.*)', raw_response, re.DOTALL)
            if match:
                content_without_brackets = match.group(1).split(', ')
                keywords_clean = [re.sub(r'["\']', '', kw).strip() for kw in content_without_brackets]
                return [kw for kw in keywords_clean if kw]
            return []

        content_without_brackets = raw_response[1:-1]
        keywords_dirty = re.split(r'["\'],\s*["\']', content_without_brackets)
        keywords_clean = []
        for keyword in keywords_dirty:
            clean_kw = keyword.strip().strip("'\"")
            if clean_kw:
                keywords_clean.append(clean_kw)
        return keywords_clean

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return []


def extract_keywords_from_scraped_text(
        consolidated_text: str,
        max_keywords: int = 100
) -> List[str]:
    if not consolidated_text:
        return []
    chunks = _split_text_into_chunks(consolidated_text)
    all_keywords = set()
    logging.info(f"Divided text into {len(chunks)} chunks for processing.")

    for i, chunk in enumerate(chunks):
        if len(all_keywords) >= max_keywords:
            logging.info(f"🎉 Reached max_keywords limit of {max_keywords}. Stopping processing.")
            break

        logging.info(f"Processing chunk {i + 1}/{len(chunks)} (size: {len(chunk)} characters)...")
        keywords_from_chunk = _extract_keywords_from_chunk(text_chunk=chunk)
        for keyword in keywords_from_chunk:
            normalized_keyword = keyword.lower().strip()
            if normalized_keyword:
                all_keywords.add(normalized_keyword)
        time.sleep(0.5)

    return list(all_keywords)[:max_keywords]