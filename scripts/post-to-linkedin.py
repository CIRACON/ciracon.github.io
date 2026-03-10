#!/usr/bin/env python3
"""Post a new insight article to LinkedIn when it merges to main.

Usage:
    python scripts/post-to-linkedin.py insights/insight-my-article.html

Required environment variables:
    LINKEDIN_ACCESS_TOKEN  – OAuth 2.0 token with w_member_social scope
    LINKEDIN_PERSON_URN    – e.g. "urn:li:person:AbCdEf123" (your LinkedIn member ID)
    SITE_URL               – Base URL of the site (default: https://www.ciracon.com)
"""

import os
import re
import sys
from html import unescape

import requests

LINKEDIN_API = "https://api.linkedin.com/rest/posts"
SITE_URL = os.environ.get("SITE_URL", "https://www.ciracon.com")


def extract_metadata(html_path: str) -> dict:
    """Extract title and description from the article HTML."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    title_match = re.search(r"<title>(.+?)\s*\|\s*Ciracon</title>", html)
    desc_match = re.search(r'<meta\s+name="description"\s+content="(.+?)"', html)
    category_match = re.search(
        r'<div class="eyebrow[^"]*"[^>]*>.*?</span>\s*(.+?)\s*</div>', html
    )

    title = unescape(title_match.group(1).strip()) if title_match else "New Insight"
    description = unescape(desc_match.group(1).strip()) if desc_match else ""
    category = (
        unescape(category_match.group(1).strip()) if category_match else "Engineering"
    )

    # Build canonical URL from file path
    filename = os.path.basename(html_path)
    url = f"{SITE_URL}/insights/{filename}"

    return {
        "title": title,
        "description": description,
        "category": category,
        "url": url,
    }


def build_post_text(meta: dict) -> str:
    """Build the LinkedIn post text."""
    lines = [
        f"{meta['title']}",
        "",
        meta["description"],
        "",
        f"Read the full article: {meta['url']}",
        "",
        f"#{meta['category'].replace(' ', '')} #Engineering #Ciracon",
    ]
    return "\n".join(lines)


def post_to_linkedin(meta: dict) -> None:
    """Publish a link post via the LinkedIn Posts API (v2, REST)."""
    access_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    person_urn = os.environ["LINKEDIN_PERSON_URN"]

    post_text = build_post_text(meta)

    payload = {
        "author": person_urn,
        "commentary": post_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "article": {
                "source": meta["url"],
                "title": meta["title"],
                "description": meta["description"],
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202601",
    }

    resp = requests.post(LINKEDIN_API, json=payload, headers=headers, timeout=30)

    if resp.status_code in (200, 201):
        print(f"Successfully posted to LinkedIn: {meta['title']}")
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"Post ID: {post_id}")
    else:
        print(f"LinkedIn API error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: post-to-linkedin.py <path-to-article.html>", file=sys.stderr)
        sys.exit(1)

    html_path = sys.argv[1]
    if not os.path.exists(html_path):
        print(f"File not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    meta = extract_metadata(html_path)
    print(f"Article: {meta['title']}")
    print(f"URL: {meta['url']}")
    print(f"Category: {meta['category']}")

    post_to_linkedin(meta)


if __name__ == "__main__":
    main()
