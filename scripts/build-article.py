#!/usr/bin/env python3
"""
Build an article HTML page from a Markdown file in articles/ and add a card
to insights.html.

Usage:
    python scripts/build-article.py articles/2026-03-10-some-title.md

Reads YAML frontmatter (title, category, description, date, slug) and the
HTML body content, then generates the full article page and prepends a card
to the insights grid.
"""

import os
import re
import sys
import math

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_frontmatter(filepath: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a Markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        print(f"Error: No frontmatter found in {filepath}", file=sys.stderr)
        sys.exit(1)

    frontmatter_text = match.group(1)
    body = match.group(2).strip()

    meta = {}
    for line in frontmatter_text.strip().split("\n"):
        key_match = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', line)
        if key_match:
            meta[key_match.group(1)] = key_match.group(2)

    return meta, body


def estimate_read_time(html_body: str) -> int:
    """Estimate read time in minutes from HTML content."""
    text = re.sub(r"<[^>]+>", "", html_body)
    word_count = len(text.split())
    return max(1, math.ceil(word_count / 230))


def build_article_page(meta: dict, body: str) -> str:
    """Generate the full HTML article page."""
    title = meta.get("title", "Untitled")
    category = meta.get("category", "AI Engineering")
    description = meta.get("description", "")
    slug = meta.get("slug", "article")
    read_time = estimate_read_time(body)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Ciracon</title>
  <meta name="description" content="{description}">
  <link rel="icon" href="../favicon.ico" type="image/x-icon">
  <link rel="canonical" href="https://www.ciracon.com/insights/insight-{slug}.html">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/styles.css">
</head>
<body>

  <!-- Navigation -->
  <nav class="nav">
    <div class="nav-inner">
      <a href="../index.html" class="logo"><span class="accent">C</span>ira<span class="accent">c</span>on</a>
      <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
      <div class="nav-links">
        <a href="../index.html">Home</a>
        <a href="../services.html">Services</a>
        <a href="../engagements.html">Work</a>
        <a href="../about.html">About</a>
        <a href="../insights.html" class="active">Insights</a>
        <a href="../contact.html" class="nav-cta"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>Let\u2019s Talk</a>
      </div>
    </div>
  </nav>

  <!-- Page Header -->
  <header class="page-header page-header-compact">
    <div class="container">
      <div class="eyebrow eyebrow-accent reveal"><span class="eyebrow-dot"></span> {category}</div>
      <h1 class="reveal reveal-delay-1">{title}</h1>
      <p class="lead reveal reveal-delay-2">{description}</p>
    </div>
  </header>

  <!-- Article Content -->
  <section class="section section-darker">
    <div class="article-content">
      <a href="../insights.html" class="article-back">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        All insights
      </a>

      <div class="article-meta">
        <span>{category}</span>
        <span>{read_time} min read</span>
      </div>

      <div>
        {body}
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <div class="footer-grid">
      <div class="footer-brand">
        <div class="logo"><span class="accent">C</span>ira<span class="accent">c</span>on</div>
        <p>Engineering-first consulting. We design, build, and operate production-grade AI and cloud platforms.</p>
      </div>
      <div>
        <h4>Services</h4>
        <div class="footer-links">
          <a href="../ai-engineering.html">AI Engineering</a>
          <a href="../platform-engineering.html">Platform Engineering</a>
          <a href="../devops-automation.html">DevOps Automation</a>
          <a href="../cloud-automation.html">Cloud &amp; Automation</a>
        </div>
      </div>
      <div>
        <h4>Company</h4>
        <div class="footer-links">
          <a href="../about.html">About</a>
          <a href="../engagements.html">Engagements</a>
          <a href="../insights.html">Insights</a>
          <a href="../contact.html">Contact</a>
        </div>
      </div>
      <div>
        <h4>Connect</h4>
        <div class="footer-links">
          <a href="mailto:info@ciracon.com">info@ciracon.com</a>
          <a href="../contact.html">Schedule a Consultation</a>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; <span id="year"></span> Ciracon. All rights reserved.</span>
      <span>AI Engineering &middot; Platform Engineering &middot; DevOps &middot; Cloud</span>
    </div>
  </footer>

  <script src="../js/main.js"></script>
</body>
</html>"""


def extract_first_paragraph(body: str) -> str:
    """Extract the text of the first <p> tag for use as the card summary."""
    match = re.search(r"<p>(.*?)</p>", body, re.DOTALL)
    if match:
        # Strip any nested HTML tags
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        # Truncate to ~160 chars at word boundary
        if len(text) > 160:
            text = text[:157].rsplit(" ", 1)[0] + "..."
        return text
    return ""


def add_card_to_insights(meta: dict, body: str):
    """Prepend a new insight card to the insights grid in insights.html."""
    insights_path = os.path.join(REPO_ROOT, "insights.html")

    with open(insights_path, "r", encoding="utf-8") as f:
        html = f.read()

    slug = meta.get("slug", "article")
    title = meta.get("title", "Untitled")
    category = meta.get("category", "AI Engineering")
    summary = meta.get("description", "") or extract_first_paragraph(body)

    # Build the new card HTML
    card = (
        f'\n        <a href="insights/insight-{slug}.html" class="insight-card reveal">\n'
        f'          <div class="insight-category">{category}</div>\n'
        f"          <h3>{title}</h3>\n"
        f"          <p>{summary}</p>\n"
        f'          <span class="insight-link">Read insight &rarr;</span>\n'
        f"        </a>\n"
    )

    # Insert after <div class="insights-grid">
    marker = '<div class="insights-grid">'
    if marker not in html:
        print("Error: Could not find insights-grid in insights.html", file=sys.stderr)
        sys.exit(1)

    html = html.replace(marker, marker + card, 1)

    with open(insights_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Added card for '{title}' to insights.html")


def main():
    if len(sys.argv) < 2:
        print("Usage: python build-article.py <path-to-article.md>", file=sys.stderr)
        sys.exit(1)

    md_path = sys.argv[1]
    if not os.path.exists(md_path):
        print(f"Error: File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    meta, body = parse_frontmatter(md_path)
    slug = meta.get("slug", "article")

    # Build HTML page
    page_html = build_article_page(meta, body)
    insights_dir = os.path.join(REPO_ROOT, "insights")
    os.makedirs(insights_dir, exist_ok=True)
    output_path = os.path.join(insights_dir, f"insight-{slug}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)
    print(f"Built article page: {output_path}")

    # Add card to insights.html
    add_card_to_insights(meta, body)

    # Output for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"page_path=insights/insight-{slug}.html\n")


if __name__ == "__main__":
    main()
