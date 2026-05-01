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

# House voice — shared across article and LinkedIn surfaces.
HOUSE_VOICE = """CIRACON HOUSE VOICE:
You write as a Ciracon engineer: 15+ years across infra, platform, and AI. You've
shipped real systems, debugged real outages, and audited a lot of half-built
platforms. You're opinionated, dry, occasionally sardonic, and you respect the
reader's time. You prefer war stories to abstractions. You name trade-offs
explicitly and you disagree with industry hype when warranted.

Voice rules:
- Short, declarative sentences. No hedging ("might", "could", "may", "potentially").
- No corporate plural ("we are pleased to", "we are excited to").
- First-person singular is fine when telling a specific story; otherwise "we" =
  Ciracon engineers, "you" = the reader.
- Concrete tool names and patterns over generic advice.
- Take positions. If you'd pick A over B, say so and say why."""

# Hook archetypes — one is selected per run and injected into the user prompt.
HOOK_ARCHETYPES = [
    {
        "name": "contrarian-claim",
        "instruction": (
            "Open with a contrarian claim that an experienced engineer would "
            "want to argue with. Format: a single sharp sentence stating what "
            "the industry gets wrong about this topic, followed by one sentence "
            "of evidence. Example shape: 'X is the wrong default for Y. Here's "
            "why teams keep reaching for it anyway.'"
        ),
    },
    {
        "name": "failure-narrative",
        "instruction": (
            "Open with a specific failure narrative from consulting experience. "
            "Format: a 2–3 sentence mini-story about something that broke in "
            "production — what we found, what it cost (time, money, or trust), "
            "and what it revealed. Use 'we' or 'a client we worked with'."
        ),
    },
    {
        "name": "surprising-stat",
        "instruction": (
            "Open with a surprising stat framed as lived experience. Format: "
            "'In the platforms we've shipped / in our audits, ~N% of [thing] "
            "[surprising outcome].' Follow with one sentence on why it matters."
        ),
    },
    {
        "name": "bold-prediction",
        "instruction": (
            "Open with a bold prediction tied to a specific timeframe. Format: "
            "'By [year], [non-obvious thing] will happen because [structural "
            "reason].' Follow with one sentence framing what to do about it now."
        ),
    },
    {
        "name": "direct-callout",
        "instruction": (
            "Open with a direct callout of a common pattern engineers will "
            "recognise from their own work. Format: name the bad pattern, then "
            "name the underlying mistake in one line. No definitions, no "
            "throat-clearing."
        ),
    },
]

# Structure archetypes — also selected per run.
STRUCTURE_ARCHETYPES = [
    {
        "name": "war-story",
        "instruction": (
            "Structure as a war story that generalises. Section flow: incident "
            "→ what we initially thought → what was actually wrong → the fix "
            "→ the broader lesson and how to apply it to similar systems. "
            "Headings should be specific to the story, not generic."
        ),
    },
    {
        "name": "contrarian-take",
        "instruction": (
            "Structure as a contrarian take. Section flow: the popular belief "
            "→ why it's wrong in the cases that matter → the conditions where "
            "it actually does hold → what we recommend instead. Make the "
            "disagreement explicit, not implied."
        ),
    },
    {
        "name": "deep-dive",
        "instruction": (
            "Structure as a focused deep dive. Section flow: the real problem "
            "(not the marketing problem) → architecture that works → trade-offs "
            "we accept → where this falls over in production → what we'd "
            "actually recommend."
        ),
    },
    {
        "name": "comparison",
        "instruction": (
            "Structure as a comparison of 2–3 named options. Section flow: "
            "what each option actually optimises for → who should pick each → "
            "the option we reach for by default and the conditions that change "
            "that pick. Avoid pros/cons lists; pick a winner per context."
        ),
    },
]

# Phrases that must not appear in the article body. These are dead corporate filler.
BANNED_PHRASES = [
    "in today's fast-paced world",
    "in this article, we will",
    "in this article we will",
    "leverage", "leveraging", "leverages",
    "unlock", "unlocking", "unlocks",
    "robust",
    "seamless", "seamlessly",
    "game-changer", "game changer",
    "best-in-class", "best in class",
    "at the end of the day",
    "it depends",
    "studies show", "research indicates", "research shows",
    "in today's", "in today's world",
    "we are pleased", "we are excited",
]

# Phrases capped at the given count per article. Going over triggers a rewrite
# request. "boring" is a useful philosophy word in moderation but became filler.
CAPPED_PHRASES = {
    "boring": 1,
    "most teams": 1,
    "what usually goes wrong": 0,   # force a creative section title instead
    "lessons learned": 0,           # ditto
}

# Required experience-framing phrases — at least ONE must appear, anchoring the
# numbers/claims to lived consulting work rather than fabricated benchmarks.
REQUIRED_EXPERIENCE_FRAMINGS = [
    "in our audits",
    "in the platforms we've shipped",
    "in the platforms we have shipped",
    "in the teams we work with",
    "a typical client we see",
    "clients we work with",
    "we've seen",
    "we have seen",
    "in our experience",
]


SYSTEM_PROMPT = """You are writing for the Ciracon engineering blog.

""" + HOUSE_VOICE + """

ARTICLE FORMAT:
- 800–1200 words.
- Clear H2 headings. Headings must be specific and earn attention — not
  "What usually goes wrong" or "Lessons learned". Use story-driven titles like
  "Where this falls over at 3am", "What we'd undo if we could", "The cheap fix
  that costs you in month six".
- Short paragraphs (2–4 sentences). Sentences that land.
- End with concrete next steps, not a sales pitch. No "In conclusion".

REQUIRED INGREDIENTS (every article must contain ALL of these):
1. At least TWO concrete numbers — latency, cost, throughput, %, time saved,
   incident count. Each number MUST be framed as lived experience using one of:
   "in our audits…", "in the platforms we've shipped…", "in the teams we work
   with…", "a typical client we see…", "we've seen…". Never use bare "studies
   show" / "research indicates" / unattributed percentages.
2. Exactly ONE explicitly contrarian sentence, signalled with one of:
   "Unpopular take:", "I'll say it:", "Here's where I disagree with the
   consensus:", "The honest answer nobody writes down:". Pick something an
   experienced engineer would push back on, and defend it in the next sentence.
3. At least ONE named real failure mode tied to a specific tool or pattern
   (e.g., "pgvector falls over once you cross ~10M rows without partitioning",
   "Bedrock + Lambda cold starts add 3–4s on the first request after idle").
4. The first TWO sentences must work as a standalone LinkedIn hook. If someone
   screenshots only the opening, it should still make an engineer want to send
   it to a colleague.

BANNED PHRASES — do not use any of these:
- "leverage", "unlock", "robust", "seamless", "game-changer", "best-in-class"
- "at the end of the day", "it depends"
- "in today's fast-paced world", "in today's…", "in this article, we will…"
- "studies show", "research indicates"
- "we are pleased to", "we are excited to"

CAPPED WORDS — do not exceed these counts:
- "boring": at most 1 use in the whole article.
- "Most teams…": at most 1 opening of this shape.
- Do NOT use the literal section headings "What usually goes wrong" or
  "Lessons learned". Write a real, specific heading instead.

OPINION AND TRADE-OFFS:
- Don't hedge. Say what you'd pick and why.
- Call out architecture mistakes by name, not by abstraction.
- When comparing approaches, declare a default and the conditions that change it.

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

Category: {category}

HOOK ARCHETYPE for this article ({hook_name}):
{hook_instruction}

STRUCTURE ARCHETYPE for this article ({structure_name}):
{structure_instruction}

Stay focused on practical knowledge engineering teams can apply to AI platforms,
DevOps, cloud infrastructure, or platform engineering. Remember the required
ingredients: two experience-framed numbers, one explicitly flagged contrarian
sentence, one named failure mode tied to a real tool, and a first two sentences
that work as a standalone LinkedIn hook. Do not use the banned phrases. Do not
exceed the capped-word limits. Do not use the literal headings "What usually
goes wrong" or "Lessons learned"."""


# ---------------------------------------------------------------------------
# Lint helpers — enforce voice rules on generated body
# ---------------------------------------------------------------------------


def _strip_html(html: str) -> str:
    """Crude tag stripper for lint passes. Lowercases output."""
    return re.sub(r"<[^>]+>", " ", html).lower()


def lint_article(body_html: str) -> list[str]:
    """Return a list of voice violations found in the article body."""
    text = _strip_html(body_html)
    violations: list[str] = []

    for phrase in BANNED_PHRASES:
        # Match as a substring; word-boundary not needed for multi-word phrases
        # but we use simple count to keep this cheap.
        if phrase in text:
            violations.append(f"Banned phrase used: '{phrase}'")

    for phrase, cap in CAPPED_PHRASES.items():
        count = text.count(phrase)
        if count > cap:
            violations.append(
                f"Phrase '{phrase}' used {count} times (cap: {cap})"
            )

    if not any(framing in text for framing in REQUIRED_EXPERIENCE_FRAMINGS):
        violations.append(
            "Missing experience framing — needs one of: "
            + ", ".join(f"'{p}'" for p in REQUIRED_EXPERIENCE_FRAMINGS[:5])
            + ", …"
        )

    # Require at least two numeric tokens (digits) in the body, so we have
    # at least two concrete numbers / metrics. Strip out diagram numbering by
    # only counting non-trivial digit groups (skip stand-alone 1/2/3 in flow
    # diagrams).
    numbers = re.findall(r"\b\d{2,}[%a-z]*\b", text)
    if len(numbers) < 2:
        violations.append(
            f"Found only {len(numbers)} concrete numbers/metrics (need ≥2)."
        )

    contrarian_markers = [
        "unpopular take",
        "i'll say it",
        "here's where i disagree",
        "the honest answer nobody",
    ]
    if not any(marker in text for marker in contrarian_markers):
        violations.append(
            "Missing flagged contrarian sentence — expected one of: "
            + ", ".join(f"'{m}'" for m in contrarian_markers)
        )

    return violations


def generate_article(topic: str, category: str, strict: bool = False) -> dict:
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

    # Step 2: pick archetypes for this run and log them
    hook = random.choice(HOOK_ARCHETYPES)
    structure = random.choice(STRUCTURE_ARCHETYPES)
    print(f"Hook archetype: {hook['name']}")
    print(f"Structure archetype: {structure['name']}")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=topic,
        category=category,
        hook_name=hook["name"],
        hook_instruction=hook["instruction"],
        structure_name=structure["name"],
        structure_instruction=structure["instruction"],
    )

    # Step 3: Generate article body
    body_response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
    )

    body_html = body_response.choices[0].message.content.strip()
    body_html = re.sub(r"^```html?\s*\n?", "", body_html)
    body_html = re.sub(r"\n?```\s*$", "", body_html)

    # Step 4: lint and (optionally) retry once
    violations = lint_article(body_html)
    if violations:
        print("Voice lint warnings:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)

        if strict:
            print("Strict mode: regenerating once to fix voice violations...",
                  file=sys.stderr)
            retry_response = client.chat.completions.create(
                model="gpt-5.4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": body_html},
                    {
                        "role": "user",
                        "content": (
                            "Rewrite the article fixing these voice violations. "
                            "Keep the topic, structure, and diagram. Output the "
                            "full article body only.\n\nViolations:\n- "
                            + "\n- ".join(violations)
                        ),
                    },
                ],
                temperature=0.8,
            )
            body_html = retry_response.choices[0].message.content.strip()
            body_html = re.sub(r"^```html?\s*\n?", "", body_html)
            body_html = re.sub(r"\n?```\s*$", "", body_html)
            remaining = lint_article(body_html)
            if remaining:
                print("Voice lint warnings after retry:", file=sys.stderr)
                for v in remaining:
                    print(f"  - {v}", file=sys.stderr)

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

    strict = "--strict" in sys.argv[1:]
    if strict:
        print("Strict mode enabled: will regenerate once if voice lint fails.")

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
    article = generate_article(topic, category, strict=strict)

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
