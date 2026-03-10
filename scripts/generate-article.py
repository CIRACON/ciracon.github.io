#!/usr/bin/env python3
"""
Discover trending topics via Google Trends and generate an article draft
using OpenAI. Outputs a Markdown file in articles/ with YAML frontmatter.

Requires:
  - OPENAI_API_KEY environment variable
"""

import os
import sys
import json
import random
import re
from datetime import datetime

from pytrends.request import TrendReq
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED_KEYWORDS = [
    "AI engineering",
    "platform engineering",
    "DevOps automation",
    "MLOps",
    "Kubernetes",
    "infrastructure as code",
    "cloud automation",
    "AI deployment",
    "developer platform",
    "LLM production",
    "RAG architecture",
    "observability",
    "CI/CD pipelines",
    "internal developer portal",
    "AI governance",
]

CATEGORIES = {
    "ai": "AI Engineering",
    "platform": "Platform Engineering",
    "devops": "DevOps Automation",
    "cloud": "Cloud Automation",
    "mlops": "AI Engineering",
    "kubernetes": "DevOps Automation",
    "llm": "AI Engineering",
    "rag": "AI Engineering",
    "terraform": "Cloud Automation",
    "infrastructure": "Cloud Automation",
    "observability": "DevOps Automation",
    "ci/cd": "DevOps Automation",
    "cicd": "DevOps Automation",
    "developer": "Platform Engineering",
    "portal": "Platform Engineering",
    "governance": "AI Engineering",
}

ARTICLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "articles")

# ---------------------------------------------------------------------------
# Topic discovery via Google Trends
# ---------------------------------------------------------------------------


def discover_topics() -> list[str]:
    """Fetch rising/top related queries from Google Trends for seed keywords."""
    pytrends = TrendReq(hl="en-US", tz=360)
    topics = set()

    # Query in batches of 5 (pytrends limit)
    for i in range(0, len(SEED_KEYWORDS), 5):
        batch = SEED_KEYWORDS[i : i + 5]
        try:
            pytrends.build_payload(batch, timeframe="today 3-m")
            related = pytrends.related_queries()
            for kw in batch:
                if kw in related and related[kw]["rising"] is not None:
                    for _, row in related[kw]["rising"].head(5).iterrows():
                        topics.add(row["query"])
                if kw in related and related[kw]["top"] is not None:
                    for _, row in related[kw]["top"].head(3).iterrows():
                        topics.add(row["query"])
        except Exception as e:
            print(f"Warning: pytrends query failed for {batch}: {e}", file=sys.stderr)
            continue

    # Fallback: if pytrends returned nothing, use seed keywords directly
    if not topics:
        print("Warning: No trending topics found, using seed keywords.", file=sys.stderr)
        topics = set(SEED_KEYWORDS)

    return list(topics)


def classify_category(topic: str) -> str:
    """Best-effort category classification based on keyword matching."""
    lower = topic.lower()
    for keyword, category in CATEGORIES.items():
        if keyword in lower:
            return category
    return "AI Engineering"  # default


# ---------------------------------------------------------------------------
# Article generation via OpenAI
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior infrastructure and AI engineer writing for a
technical blog. Your writing style:

- Direct and practical. No marketing language, no fluff, no buzzwords.
- Write like you're explaining something to a peer engineer over coffee.
- Use concrete examples, real tool names, and specific architectural patterns.
- First person plural ("we") or second person ("you") — never corporate "we are pleased to."
- Short paragraphs. Sentences that get to the point.
- Include specific technical details: tool names, configuration approaches, trade-offs.
- Structure with clear H2 headings that describe what each section covers.
- No intro like "In today's fast-paced world..." or "In this article, we will..."
- End with practical next steps, not a sales pitch.

Output format: Return ONLY the article body in HTML (using <p>, <h2>, <h3>, <ul>, <ol>,
<li>, <strong>, <em>, <code> tags). Do NOT include a title or any wrapping elements.
The article should be 800-1200 words."""

USER_PROMPT_TEMPLATE = """Write a technical article about: {topic}

The article should be relevant to engineering teams working on AI platforms, DevOps,
cloud infrastructure, or platform engineering. Focus on practical knowledge — what
actually works, common mistakes, and concrete recommendations.

Category: {category}"""


def generate_article(topic: str, category: str) -> dict:
    """Generate article content using OpenAI API. Returns title, description, and HTML body."""
    client = OpenAI()

    # Step 1: Generate title and description
    meta_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You generate concise article titles and descriptions. "
                "Return JSON with keys: title (string, 5-10 words, no clickbait), "
                "description (string, one sentence, under 160 chars).",
            },
            {
                "role": "user",
                "content": f"Generate a title and meta description for a technical "
                f"engineering article about: {topic}\nCategory: {category}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    meta = json.loads(meta_response.choices[0].message.content)
    title = meta.get("title", topic)
    description = meta.get("description", "")

    # Step 2: Generate article body
    body_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(topic=topic, category=category),
            },
        ],
        temperature=0.7,
    )

    body_html = body_response.choices[0].message.content.strip()

    # Clean up any markdown code fences the model might add
    body_html = re.sub(r"^```html?\s*\n?", "", body_html)
    body_html = re.sub(r"\n?```\s*$", "", body_html)

    return {"title": title, "description": description, "body": body_html}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def save_article(title: str, description: str, category: str, body: str) -> str:
    """Save article as a Markdown file with YAML frontmatter."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join(ARTICLES_DIR, filename)

    frontmatter = (
        f"---\n"
        f"title: \"{title}\"\n"
        f"category: \"{category}\"\n"
        f"description: \"{description}\"\n"
        f"date: \"{date_str}\"\n"
        f"slug: \"{slug}\"\n"
        f"---\n\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write(body)

    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required.", file=sys.stderr)
        sys.exit(1)

    print("Discovering trending topics...")
    topics = discover_topics()
    print(f"Found {len(topics)} candidate topics.")

    # Pick a random topic
    topic = random.choice(topics)
    category = classify_category(topic)
    print(f"Selected topic: {topic} [{category}]")

    print("Generating article...")
    article = generate_article(topic, category)

    filepath = save_article(
        title=article["title"],
        description=article["description"],
        category=category,
        body=article["body"],
    )

    print(f"Article saved: {filepath}")

    # Output for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"article_path={filepath}\n")
            f.write(f"article_title={article['title']}\n")
            f.write(f"article_category={category}\n")
            f.write(f"article_slug={slugify(article['title'])}\n")


if __name__ == "__main__":
    main()
