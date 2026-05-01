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

# Mirrors the Ciracon house voice from scripts/generate-article.py.
HOUSE_VOICE = (
    "You write as a Ciracon engineer: 15+ years across infra, platform, and AI. "
    "Opinionated, dry, occasionally sardonic, respects the reader's time. "
    "Prefers war stories to abstractions. Names trade-offs explicitly and "
    "disagrees with industry hype when warranted. Short, declarative sentences. "
    "No hedging ('might', 'could', 'may'). No corporate plural ('we are pleased "
    "to', 'we are excited to'). Concrete tool names over generic advice."
)

LINKEDIN_BANNED_PHRASES = [
    "leverage", "unlock", "robust", "seamless", "game-changer",
    "best-in-class", "at the end of the day", "it depends",
    "in today's", "studies show", "research indicates",
    "we are pleased", "we are excited", "i'm excited to share",
    "link in comments", "boring",  # boring is fully banned in 200-word posts
]


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
    h2_headings: list[str] = []
    if body_match:
        body_html = body_match.group(1)
        h2_headings = [
            unescape(re.sub(r"<[^>]+>", "", h).strip())
            for h in re.findall(r"<h2[^>]*>(.+?)</h2>", body_html, re.DOTALL)
        ]
        body_text = re.sub(r"<[^>]+>", " ", body_html)
        body_text = re.sub(r"\s+", " ", body_text).strip()[:3000]

    return {
        "title": title,
        "description": description,
        "category": category,
        "url": url,
        "body_text": body_text,
        "h2_headings": h2_headings,
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
                            HOUSE_VOICE + "\n\n"
                            "You write LinkedIn posts that drive engineers to "
                            "click through and read the full article. The first "
                            "two lines must be screenshot-shareable on their own.\n\n"
                            "STRUCTURE (follow this exactly):\n"
                            "1. HOOK (1-2 sentences): A bold, specific, contrarian, "
                            "or war-story claim drawn directly from the article. "
                            "A genuine, specific question is allowed if it's the "
                            "kind a senior engineer would actually ask in Slack — "
                            "no rhetorical openers, no 'Have you ever…'.\n"
                            "\n"
                            "2. BODY (2-3 short paragraphs): Pull out 2-3 concrete "
                            "insights, failure modes, or recommendations from the "
                            "article. At least one specific number, named tool, "
                            "or named pattern is required. Each paragraph: 2-3 "
                            "sentences max. Give away the punchline — LinkedIn "
                            "rewards complete posts. The click is for depth, not "
                            "to find out the answer.\n"
                            "\n"
                            "3. CTA (1 sentence): Direct the reader to the full "
                            "article using the exact URL provided. Do NOT say "
                            "'link in comments'.\n"
                            "\n"
                            "4. HASHTAGS (last line): 3-5 hashtags relevant to the "
                            "topic. Always include #AIEngineering, "
                            "#PlatformEngineering, or #DevOps as appropriate. "
                            "Use CamelCase for multi-word tags.\n"
                            "\n"
                            "RULES:\n"
                            "- Total length: 150-250 words (NOT counting hashtags).\n"
                            "- Separate each section with a blank line.\n"
                            "- Write in first person ('I', 'we').\n"
                            "- No emojis. No clickbait. No 'I'm excited to share'.\n"
                            "- Numbers must be framed as lived experience: "
                            "'in our audits…', 'in the platforms we've shipped…', "
                            "'we've seen…'. Never 'studies show'.\n"
                            "- Banned words: leverage, unlock, robust, seamless, "
                            "game-changer, best-in-class, boring, at the end of "
                            "the day, it depends.\n"
                            "- Do NOT start with 'Most teams…'."
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

            # Warn if banned phrases slipped through (don't block posting)
            lower = post_text.lower()
            hits = [p for p in LINKEDIN_BANNED_PHRASES if p in lower]
            if hits:
                print(
                    f"Warning: LinkedIn post contains banned phrases: {hits}",
                    file=sys.stderr,
                )

            return post_text
        except Exception as e:
            print(f"Warning: OpenAI post generation failed, using fallback: {e}", file=sys.stderr)

    # Fallback: pull the first 1-2 sentences of the article body as the hook,
    # then list 2 H2 headings as takeaways. Better than just title + description.
    category_tag = meta["category"].replace(" ", "")
    body_text = meta.get("body_text", "") or meta.get("description", "")
    sentences = re.split(r"(?<=[.!?])\s+", body_text.strip())
    hook = " ".join(sentences[:2]).strip() or meta["title"]

    takeaway_lines = []
    for heading in (meta.get("h2_headings") or [])[:2]:
        takeaway_lines.append(f"- {heading}")

    parts = [hook, ""]
    if takeaway_lines:
        parts.append("In the article:")
        parts.extend(takeaway_lines)
        parts.append("")
    parts.extend([
        f"Read the full article: {meta['url']}",
        "",
        f"#{category_tag} #Engineering #Ciracon",
    ])
    return "\n".join(parts)


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
