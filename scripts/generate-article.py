#!/usr/bin/env python3
"""
Discover trending topics via SerpAPI Google Trends and generate an article
draft using OpenAI. Outputs a Markdown file in articles/ with YAML frontmatter.

Requires:
  - OPENAI_API_KEY environment variable
  - SERPAPI_KEY environment variable
"""

import os
import sys
import json
import random
import re
import time
from datetime import datetime

from serpapi import GoogleSearch
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

# Topics containing these words are almost never relevant — reject early.
BLOCKED_KEYWORDS = [
    "news today", "breaking news", "news for", "latest news",
    "business news", "tech news", "news overview", "news roundup",
    "stock price", "stock market", "crypto", "bitcoin", "ethereum",
    "tiktok", "instagram", "snapchat", "facebook", "twitter",
    "apple news", "fox news", "cnn", "nfl", "nba", "mlb",
    "movie", "trailer", "celebrity", "kardashian", "weather",
    "horoscope", "lottery", "recipe", "diet",
    "book review", "book for",
]

MAX_TOPIC_ATTEMPTS = 10  # how many topics to try before giving up

# ---------------------------------------------------------------------------
# Topic discovery via SerpAPI Google Trends
# ---------------------------------------------------------------------------


def discover_topics() -> list[str]:
    """Fetch related queries from Google Trends via SerpAPI for seed keywords."""
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        print("Warning: SERPAPI_KEY not set, using seed keywords.", file=sys.stderr)
        return list(SEED_KEYWORDS)

    topics = set()

    for keyword in SEED_KEYWORDS:
        try:
            results = GoogleSearch({
                "engine": "google_trends",
                "q": keyword,
                "data_type": "RELATED_QUERIES",
                "api_key": api_key,
            }).get_dict()
            for group in results.get("related_queries", {}).get("rising", []):
                topics.add(group.get("query", ""))
            for group in results.get("related_queries", {}).get("top", []):
                topics.add(group.get("query", ""))
        except Exception as e:
            print(f"Warning: SerpAPI query failed for '{keyword}': {e}", file=sys.stderr)
            continue
        time.sleep(1)  # pace requests

    topics.discard("")

    # Fallback: if nothing found, use seed keywords directly
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


def is_blocked_topic(topic: str) -> bool:
    """Fast check: reject topics that match known irrelevant patterns."""
    lower = topic.lower()
    return any(kw in lower for kw in BLOCKED_KEYWORDS)


def is_relevant_topic(topic: str) -> bool:
    """Use OpenAI to decide whether a trending topic is genuinely relevant
    to infrastructure, DevOps, platform engineering, or AI engineering.
    Returns True only for topics that can produce a substantive technical article."""
    if is_blocked_topic(topic):
        print(f"  Blocked by keyword filter: {topic}")
        return False

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You evaluate whether a topic is suitable for a technical "
                    "engineering blog focused on: AI/ML engineering, platform "
                    "engineering, DevOps, cloud infrastructure, and MLOps.\n\n"
                    "REJECT topics that are:\n"
                    "- General news roundups or current-events commentary\n"
                    "- Pop culture, entertainment, sports, finance, or crypto\n"
                    "- Product announcements with no actionable engineering depth\n"
                    "- Broad/vague (e.g. 'Artificial Intelligence News')\n"
                    "- Primarily about a non-engineering product even if loosely "
                    "connected to tech (e.g. 'Adobe Creative Cloud News')\n\n"
                    "ACCEPT topics that would let an engineer write 800+ words of "
                    "concrete, practical technical guidance with real architecture "
                    "patterns, tool recommendations, or failure-mode analysis.\n\n"
                    "Return JSON: {\"relevant\": true/false, \"reason\": \"one sentence\"}"
                ),
            },
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_completion_tokens=100,
    )

    result = json.loads(response.choices[0].message.content)
    relevant = result.get("relevant", False)
    reason = result.get("reason", "")
    print(f"  Relevance check: {topic} -> {'PASS' if relevant else 'REJECT'} ({reason})")
    return relevant


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

OPINION AND EXPERIENCE:
- Take positions on trade-offs. Don't hedge with "it depends" — say what you'd actually recommend and why.
- Include at least one "Lessons learned" or "Common failure modes" section that describes what typically goes wrong and why.
- Replace generic advice with authoritative opinions grounded in real-world experience.
  BAD: "Organizations implementing RAG should consider scalability."
  GOOD: "Most production RAG systems fail because teams optimize retrieval before they build evaluation loops."
- Call out architecture mistakes you've seen. Mention the failure mode, not just the best practice.
- When comparing approaches, state which one you'd pick for a given context and why — don't just list pros and cons.

DIAGRAM REQUIREMENT: Include exactly ONE diagram early in the article (before the first
H2 or after the first section) using this HTML structure. Choose the best diagram type
for the topic:

Flow diagram (for pipelines, sequences):
<div class="diagram">
  <div class="diagram-title">LABEL HERE</div>
  <div class="diagram-flow">
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">1</span>
        <span class="node-label">Step 1</span>
        <span class="node-sub">Subtitle</span>
        <span class="node-tooltip">One-sentence explanation of this step shown on hover.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">2</span>
        <span class="node-label">Step 2</span>
        <span class="node-sub">Subtitle</span>
        <span class="node-tooltip">One-sentence explanation of this step shown on hover.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-node">
      <span class="node-num">3</span>
      <span class="node-label">Final Step</span>
      <span class="node-sub">Subtitle</span>
      <span class="node-tooltip">One-sentence explanation of this step shown on hover.</span>
    </div>
  </div>
  <div class="diagram-hint">Hover over each step for details</div>
</div>

Stack diagram (for layers, maturity models):
<div class="diagram">
  <div class="diagram-title">LABEL HERE</div>
  <div class="diagram-stack">
    <div class="diagram-stack-layer">
      <span class="diagram-stack-label">LAYER</span>
      <div class="diagram-stack-items"><span>Item 1</span><span>Item 2</span></div>
      <span class="node-tooltip">One-sentence explanation of this layer shown on hover.</span>
    </div>
    <!-- repeat per layer, top-down order -->
  </div>
  <div class="diagram-hint">Hover over each layer for details</div>
</div>

Comparison diagram (for vs, before/after):
<div class="diagram">
  <div class="diagram-title">LABEL HERE</div>
  <div class="diagram-compare">
    <div class="diagram-compare-col diagram-col-muted">
      <h4>Option A</h4>
      <ul><li><span class="cmp-icon">&ndash;</span> Point 1</li><li><span class="cmp-icon">&ndash;</span> Point 2</li></ul>
    </div>
    <div class="diagram-compare-col diagram-col-accent">
      <h4>Option B</h4>
      <ul><li><span class="cmp-icon">&check;</span> Point 1</li><li><span class="cmp-icon">&check;</span> Point 2</li></ul>
    </div>
  </div>
</div>

Cycle diagram (for iterative processes):
<div class="diagram">
  <div class="diagram-title">LABEL HERE</div>
  <div class="diagram-cycle">
    <div class="diagram-cycle-step">
      <div class="diagram-cycle-node">Step 1<span class="node-tooltip">One-sentence explanation of this phase shown on hover.</span></div>
      <div class="diagram-cycle-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-cycle-step">
      <div class="diagram-cycle-node">Step 2<span class="node-tooltip">One-sentence explanation of this phase shown on hover.</span></div>
      <div class="diagram-cycle-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-cycle-node">Step 1<span class="node-tooltip">The cycle repeats from here.</span></div>
  </div>
  <div class="diagram-hint">Hover over each phase for details</div>
</div>

Output format: Return ONLY the article body in HTML (using <p>, <h2>, <h3>, <ul>, <ol>,
<li>, <strong>, <em>, <code> tags, and one diagram). Do NOT include a title or any
wrapping elements. The article should be 800-1200 words."""

USER_PROMPT_TEMPLATE = """Write a technical article about: {topic}

The article should be relevant to engineering teams working on AI platforms, DevOps,
cloud infrastructure, or platform engineering. Focus on practical knowledge — what
actually works, common mistakes, and concrete recommendations.

Include engineering opinions based on real-world experience. State what typically goes
wrong, what trade-offs matter, and what you'd actually recommend. Add a "Lessons learned"
or "What usually goes wrong" section with specific failure modes.

Category: {category}"""


def generate_article(topic: str, category: str) -> dict:
    """Generate article content using OpenAI API. Returns title, description, and HTML body."""
    client = OpenAI()

    # Step 1: Generate title and description
    meta_response = client.chat.completions.create(
        model="gpt-5.4",
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
        model="gpt-5.4",
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

    # Shuffle and pick the first topic that passes relevance checks
    random.shuffle(topics)
    topic = None
    category = None
    for i, candidate in enumerate(topics[:MAX_TOPIC_ATTEMPTS]):
        print(f"Evaluating candidate {i + 1}/{min(len(topics), MAX_TOPIC_ATTEMPTS)}: {candidate}")
        if not is_relevant_topic(candidate):
            continue
        topic = candidate
        category = classify_category(topic)
        print(f"Selected topic: {topic} [{category}]")
        break

    if topic is None:
        print("Error: No relevant topic found after checking candidates.", file=sys.stderr)
        sys.exit(1)

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
