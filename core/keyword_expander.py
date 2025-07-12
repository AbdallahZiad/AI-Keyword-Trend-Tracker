import time
import json
from typing import List, Dict, Optional
from config import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def expand_keyword(keyword: str, n: int = 5, model="gpt-3.5-turbo") -> List[str]:
    """
    Use OpenAI GPT to generate N similar keywords to a given keyword.
    """
    prompt = (
        f"You are a keyword research expert helping build a trend detection tool.\n\n"
        f"Given the keyword: \"{keyword}\", generate {n} realistic search queries that people would "
        "use in search engines like Google when looking for the same thing or related products.\n\n"
        "Each result must be:\n"
        "- Short and concise (2 to 4 words)\n"
        "- Naturally typed by real users (no fluff, no jargon, no marketing phrases)\n"
        "- Related to the same intent (including synonyms, slang, or product types)\n\n"
        "Examples:\n"
        "Input: \"budget gaming laptop\"\n"
        "Output: [\"cheap gaming laptop\", \"affordable gaming laptop\", \"low-cost gaming laptop\", \"entry level gaming laptop\", \"best gaming laptops under 500\"]\n\n"
        f"Now do the same for: \"{keyword}\"\n"
        "Return only a valid Python list of strings. No explanations."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100,
        )
        raw = response.choices[0].message.content
        result = eval(raw.strip(), {"__builtins__": None}, {})  # Expected list output
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[ERROR] Failed to expand keyword '{keyword}': {e}")
        return []


def expand_keywords_batch(
    keywords: List[str],
    n: int = 5,
    delay: float = 1.1,
    model: str = "gpt-3.5-turbo"
) -> List[Dict[str, List[str]]]:
    """
    Expand a list of keywords into a list of dictionaries with similar keywords.
    """
    results = []
    for kw in keywords:
        print(f"🔍 Expanding: {kw}")
        similar = expand_keyword(kw, n=n, model=model)
        results.append({
            "keyword": kw,
            "similar_keywords": similar
        })
        time.sleep(delay)  # avoid OpenAI rate limiting
    return results


def save_expanded_keywords_to_file(
    expanded: List[Dict[str, List[str]]],
    path: str
) -> None:
    """
    Save expanded keyword data to a JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(expanded, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved expanded keywords to {path}")


if __name__ == "__main__":
    # Demo mode: run with sample data
    sample_keywords = [
        "portable grills",
        "ai marketing",
        "budget gaming laptop"
    ]
    expanded = expand_keywords_batch(sample_keywords, n=5)
    print(json.dumps(expanded, indent=2))
    save_expanded_keywords_to_file(expanded, "data/expanded_keywords.json")
