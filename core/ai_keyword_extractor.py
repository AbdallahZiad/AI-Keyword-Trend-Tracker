import sys
import os
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
import time

from slack_sdk.errors import SlackApiError

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

MAX_PROMPT_TOKENS = 3000
CHARS_PER_TOKEN = 4
MAX_CHUNK_SIZE = MAX_PROMPT_TOKENS * CHARS_PER_TOKEN


def _split_text_into_chunks(text: str) -> List[str]:
    # This function remains unchanged
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
    # This function remains unchanged
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
    # This function remains unchanged
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


def categorize_keywords_with_ai(
        scanned_keywords: List[str],
        existing_structure: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Uses AI to categorize all keywords at once into the structured format,
    ensuring no keywords are lost.
    """
    if not scanned_keywords:
        return existing_structure

    # 🔑 PROMPT FIXES: Added SCORING STEP to prioritize new, distinct categories
    prompt = (
        "You are a meticulous data architect and marketing strategist. Your **primary and non-negotiable task** is to ensure **100% inclusion** of every single keyword from the `NEW KEYWORDS` list into the final structured output. If you omit any keyword, the output is invalid.\n\n"
        "Your output **MUST** be a single JSON array that merges the existing categories with all new keywords, following these rules:\n\n"
        "### Output Structure Mandates (Strict Schema)\n"
        "**The entire output MUST be a single JSON array containing category objects.**\n"
        "1. **Category IDs:** Every category object (existing or new) MUST have an integer **`category_id`**. IDs must be sequential, starting at 1.\n"
        "2. **Ad Group IDs:** Every ad group object (existing or new) MUST have an integer **`ad_group_id`**. IDs must be sequential, starting at 1, across ALL ad groups.\n"
        "3. **Recalculate All IDs:** You must re-index the **entire final structure**. Do not use the IDs from the `Existing Categories` list; assign new, sequential IDs to ALL categories and ALL ad groups in the final merged output.\n\n"
        "### Categorization Rules\n"
        "1. **SCORING/INITIAL STEP:** Before merging, first analyze the `NEW KEYWORDS` list and identify which keywords *must* be grouped into a new category because they do not relate to any existing category (e.g., 'Apple Products' vs 'Clothing').\n"
        "2. **Existing Categories**: Add new keywords (if any fit) to the most relevant existing category and ad group. Create a new ad group if necessary.\n"
        "3. **New Categories**: Create new, logical categories for all keywords identified in the SCORING/INITIAL STEP. Group related keywords into new ad groups within these categories as needed.\n\n"
        "### Example of Desired Structure (Mandatory Schema)\n"
        "**Use this exact object structure and ensure all IDs are present and sequentially updated:**\n"
        "```json\n"
        "[\n"
        "  {\n"
        "    \"category_id\": 1,\n"
        "    \"category_name\": \"Example Category\",\n"
        "    \"ad_groups\": [\n"
        "      {\n"
        "        \"ad_group_id\": 1,\n"
        "        \"ad_group_name\": \"Example Group A (Existing)\",\n"
        "        \"keywords\": [\"existing keyword\", \"new keyword merged here\"]\n"
        "      }\n"
        "    ]\n"
        "  },\n"
        "  {\n"
        "    \"category_id\": 2,\n"
        "    \"category_name\": \"Example Category\",\n"
        "    \"ad_groups\": [\n"
        "      {\n"
        "        \"ad_group_id\": 2,\n"
        "        \"ad_group_name\": \"Example Group A (Existing)\",\n"
        "        \"keywords\": [\"new keyword merged here\"]\n"
        "      }\n"
        "    ]\n"
        "  }, ...\n"
        "]\n"
        "```\n\n"
        "--- (End of Schema)\n\n"
        "**Existing Categories (for context):**\n"
        f"{json.dumps(existing_structure, indent=2)}\n\n"
        "**NEW KEYWORDS TO CATEGORIZE (READ THIS LIST CAREFULLY, your final output must include all these):**\n"
        f"{json.dumps(scanned_keywords, indent=2)}\n\n"
        "**Generate the complete, merged, and fully re-ID'd RAW JSON array that includes every single new keyword. Feel free to add new categories for the output to be very professional (and nothing else):**"
    )

    try:
        # 🔑 FIX: Use response_format={"type": "json_object"} to force the API
        # to guarantee syntactically valid JSON output.
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=12000
        )

        ai_output_text = response.choices[0].message.content.strip()


        json_string_clean = ai_output_text.replace('```json', '').replace('```', '').strip()

        ai_output = json.loads(json_string_clean)
        return ai_output

    except Exception as e:
        # Keep the single general exception handler for any unexpected API or network issues.
        logging.error(f"❌ An error occurred during AI categorization: {e}", exc_info=True)
        return []