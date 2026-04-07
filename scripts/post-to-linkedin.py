#!/usr/bin/env python3
"""Post a new insight article to LinkedIn when it merges to main.

Usage:
    python scripts/post-to-linkedin.py insights/insight-my-article.html

Required environment variables:
    LINKEDIN_ACCESS_TOKEN  – OAuth 2.0 token with w_member_social scope
    LINKEDIN_PERSON_URN    – e.g. "urn:li:person:AbCdEf123" (your LinkedIn member ID)
    SITE_URL               – Base URL of the site (default: https://www.ciracon.com)
    OPENAI_API_KEY         – For generating engaging post text
"""

import os
import re
import sys
from html import unescape

import requests
from openai import OpenAI

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

    # Extract article body text for post generation
    body_match = re.search(
        r'<div class="article-content">(.+?)</section>',
        html,
        re.DOTALL,
    )
    body_text = ""
    if body_match:
        body_text = re.sub(r"<[^>]+>", " ", body_match.group(1))
        body_text = re.sub(r"\s+", " ", body_text).strip()[:3000]

    return {
        "title": title,
        "description": description,
        "category": category,
        "url": url,
        "body_text": body_text,
    }


def build_post_text(meta: dict) -> str:
    """Generate a compelling LinkedIn post using OpenAI.

    Falls back to a simple template if the API call fails.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key and meta.get("body_text"):
        try:
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-5.4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You write LinkedIn posts for a senior engineer at a "
                            "technical consulting company. The post must drive "
                            "engineers to click through and read the full article.\n\n"
                            "STRUCTURE (follow this exactly):\n"
                            "1. HOOK (1-2 sentences): A bold, specific, or contrarian "
                            "claim drawn from the article. Not a question. Not generic.\n"
                            "\n"
                            "2. BODY (2-3 short paragraphs): Pull out 2-3 concrete "
                            "insights, failure modes, or practical recommendations from "
                            "the article. Use specific tool names, patterns, or numbers "
                            "when available. Each paragraph should be 2-3 sentences max.\n"
                            "\n"
                            "3. CTA (1 sentence): Direct the reader to the full article "
                            "using the exact URL provided.\n"
                            "\n"
                            "4. HASHTAGS (last line): 3-5 hashtags relevant to the topic. "
                            "Always include #AIEngineering or #PlatformEngineering or "
                            "#DevOps as appropriate. Use CamelCase for multi-word tags.\n"
                            "\n"
                            "RULES:\n"
                            "- Total length: 150-250 words (NOT counting hashtags).\n"
                            "- Separate each section with a blank line.\n"
                            "- Write in first person ('I', 'we').\n"
                            "- No emojis. No clickbait. No 'I'm excited to share'.\n"
                            "- Do NOT say 'link in comments'.\n"
                            "- Do NOT start with a question."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Write a LinkedIn post for this article:\n\n"
                            f"Title: {meta['title']}\n"
                            f"Category: {meta['category']}\n"
                            f"Description: {meta['description']}\n"
                            f"URL: {meta['url']}\n\n"
                            f"Article content (excerpt):\n{meta['body_text'][:2000]}"
                        ),
                    },
                ],
                temperature=0.7,
                max_completion_tokens=600,
            )
            post_text = response.choices[0].message.content.strip()

            # Ensure the URL is in the post
            if meta["url"] not in post_text:
                post_text += f"\n\n{meta['url']}"

            # Ensure hashtags are present — append defaults if missing
            if "#" not in post_text.split("\n")[-1]:
                tag = meta["category"].replace(" ", "")
                post_text += f"\n\n#{tag} #Engineering #Ciracon"

            return post_text
        except Exception as e:
            print(f"Warning: OpenAI post generation failed, using fallback: {e}", file=sys.stderr)

    # Fallback: simple template
    category_tag = meta["category"].replace(" ", "")
    lines = [
        f"{meta['title']}",
        "",
        meta["description"],
        "",
        f"Read the full article: {meta['url']}",
        "",
        f"#{category_tag} #Engineering #Ciracon",
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
