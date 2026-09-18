import os
import re

import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from readability import Document
from requests.exceptions import HTTPError, Timeout
from tavily import TavilyClient

load_dotenv(encoding="utf-8")

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic . Returns Titles , URLs and snippets."""
    results = tavily.search(query=query, max_results=5)

    out = []

    for r in results['results']:
        out.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}\n")

    return "\n----\n".join(out)

def _sanitize_html(html: str) -> str:
    """Remove characters XML parsers reject, keeping tab, newline and carriage return."""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html)


def _text_from_tags(raw_html: str) -> str:
    """Strip non-content tags and collapse the remaining text into one line."""
    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form"
    ]):
        tag.decompose()

    return re.sub(r'\s+', ' ', soup.get_text(separator=" ", strip=True))


@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract clean readable content from a URL.
    Uses multiple extraction strategies for better reliability.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    # fetch stage: network failures should return immediately instead of
    # falling through to the extraction strategies
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()
    except Timeout:
        return "Request timed out while scraping the URL."
    except HTTPError as e:
        return f"HTTP error occured: {e!s}"
    except Exception as e:
        return f"Could not fetch URL: {e!s}"

    html = _sanitize_html(response.text)

    # extraction stage: each strategy is isolated so that a strategy raising
    # an exception falls through to the next one instead of aborting the chain

    # strategy1: trafilatura (best for atricles/blogs)
    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
        )

        if extracted and len(extracted.strip()) > 200:
            return re.sub(r'\s+', ' ', extracted)[:5000]
    except Exception as e:
        print(f"[scrape_url] trafilatura failed: {e!s}")

    # strategy2: readability
    try:
        text = _text_from_tags(Document(html).summary())

        if len(text) > 200:
            return text[:5000]
    except Exception as e:
        print(f"[scrape_url] readability failed: {e!s}")

    # strategy3: fallback full page extraction
    try:
        text = _text_from_tags(html)

        if text:
            return text[:5000]
    except Exception as e:
        print(f"[scrape_url] full-page extraction failed: {e!s}")

    return "Could not extract meaningful content from the page."