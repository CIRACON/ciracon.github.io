#!/usr/bin/env python3
"""
Apply SEO metadata to every page and regenerate sitemap.xml.

Idempotent: safe to run any number of times. It manages content between
marker comments so hand-written page content is never touched:

  <!-- seo:start --> ... <!-- seo:end -->          (in <head>)
  <!-- related:start --> ... <!-- related:end -->  (article pages only)

What it does for each HTML page:
  - Open Graph + Twitter card tags (with a shared default share image)
  - JSON-LD structured data (Organization, WebSite, Service, Article,
    BreadcrumbList, etc.)
  - A tiny inline script that adds the `js` class to <html> so scroll-reveal
    animations only hide content when JavaScript is actually running
  - <main> landmark + skip link for accessibility
  - For insight articles: visible publish date, a CTA to the related service
    page, and "Related insights" links to articles in the same category

Then writes sitemap.xml with every indexable page.

Usage:
    python scripts/seo_build.py
"""

import html
import json
import os
import re
import subprocess
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.ciracon.com"
OG_IMAGE = f"{SITE}/images/og-default.png"
ORG_ID = f"{SITE}/#organization"

# Pages that should not be indexed or listed in the sitemap.
EXCLUDE = {"404.html", "devops-platform-engineering.html"}

ORGANIZATION = {
    "@type": "ProfessionalService",
    "@id": ORG_ID,
    "name": "Ciracon",
    "legalName": "Ciracon LLC",
    "url": f"{SITE}/",
    "logo": f"{SITE}/images/apple-touch-icon.png",
    "image": OG_IMAGE,
    "description": (
        "Engineering-first consulting firm that designs and delivers "
        "production-grade AI platforms, platform engineering, DevOps "
        "automation, and cloud infrastructure."
    ),
    "email": "info@ciracon.com",
    "foundingDate": "2012",
    "founder": {"@type": "Person", "name": "Ola Ekdahl",
                "jobTitle": "Founder & Principal Engineer",
                "sameAs": ["https://www.linkedin.com/in/olaekdahl",
                           "https://github.com/olaekdahl"]},
    "address": {"@type": "PostalAddress", "addressLocality": "Irvine",
                "addressRegion": "CA", "addressCountry": "US"},
    "areaServed": "Worldwide",
    "knowsAbout": [
        "AI engineering", "Retrieval-augmented generation", "LLM operations",
        "Platform engineering", "Internal developer platforms", "Kubernetes",
        "DevOps automation", "CI/CD", "GitOps", "Observability",
        "Infrastructure as Code", "Terraform", "AWS", "Azure",
    ],
    "sameAs": ["https://www.linkedin.com/company/ciracon-llc",
               "https://github.com/CIRACON"],
}

# Service pages -> Service schema
SERVICES = {
    "ai-engineering.html": "AI Engineering",
    "platform-engineering.html": "Platform Engineering",
    "devops-automation.html": "DevOps Automation",
    "cloud-automation.html": "Cloud Architecture & Automation",
}

# Article category -> (service page, label)
CATEGORY_SERVICE = {
    "AI Engineering": ("ai-engineering.html", "AI Engineering"),
    "Platform Engineering": ("platform-engineering.html", "Platform Engineering"),
    "DevOps Automation": ("devops-automation.html", "DevOps Automation"),
    "Cloud Automation": ("cloud-automation.html", "Cloud Architecture & Automation"),
}

PAGE_NAMES = {
    "services.html": "Services", "engagements.html": "Work",
    "about.html": "About", "insights.html": "Insights",
    "contact.html": "Contact", **SERVICES,
}

PAGE_TYPES = {
    "about.html": "AboutPage", "contact.html": "ContactPage",
    "insights.html": "CollectionPage",
}


# ── helpers ────────────────────────────────────────────────────────────────

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def meta(page, name, attr="name"):
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else ""


def title_of(page):
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def h1_of(page):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def git_date(path, first=False):
    args = ["git", "-C", REPO_ROOT, "log", "--format=%as"]
    if first:
        args += ["--diff-filter=A"]
    args += ["--", os.path.relpath(path, REPO_ROOT)]
    try:
        out = subprocess.run(args, capture_output=True, text=True).stdout.split()
    except OSError:
        out = []
    if not out:
        return date.today().isoformat()
    return out[-1] if first else out[0]


def article_date(slug, path):
    """Publish date: from articles/YYYY-MM-DD-<slug>.md, else first git commit."""
    md_dir = os.path.join(REPO_ROOT, "articles")
    for name in sorted(os.listdir(md_dir)):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", name)
        if m and m.group(2) == slug:
            return m.group(1)
    return git_date(path, first=True)


def esc(s):
    return html.escape(s, quote=True)


def jsonld(obj):
    data = json.dumps(obj, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{data}\n</script>'


def breadcrumb(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(items)
        ],
    }


# ── per-page processing ────────────────────────────────────────────────────

def build_head_block(rel, page, canonical, article=None):
    title = title_of(page)
    desc = meta(page, "description")
    og_type = "article" if article else "website"
    tags = [
        '<meta name="theme-color" content="#0B0F14">',
        f'<link rel="apple-touch-icon" href="/images/apple-touch-icon.png">',
        '<meta property="og:site_name" content="Ciracon">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Ciracon — Build the infrastructure for production AI">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
    ]
    if rel in EXCLUDE:
        tags.insert(0, '<meta name="robots" content="noindex, follow">')

    graph = []
    home = ("Home", f"{SITE}/")
    if rel == "index.html":
        graph.append(ORGANIZATION)
        graph.append({"@type": "WebSite", "@id": f"{SITE}/#website",
                      "url": f"{SITE}/", "name": "Ciracon",
                      "publisher": {"@id": ORG_ID}})
    elif article:
        tags += [
            f'<meta property="article:published_time" content="{article["date"]}">',
            f'<meta property="article:modified_time" content="{article["modified"]}">',
            f'<meta property="article:section" content="{esc(article["category"])}">',
        ]
        graph.append({
            "@type": "BlogPosting",
            "@id": f"{canonical}#article",
            "headline": article["headline"],
            "description": desc,
            "image": OG_IMAGE,
            "datePublished": article["date"],
            "dateModified": article["modified"],
            "articleSection": article["category"],
            "author": {"@id": ORG_ID, "@type": "Organization", "name": "Ciracon"},
            "publisher": {"@id": ORG_ID, "@type": "Organization", "name": "Ciracon",
                          "logo": {"@type": "ImageObject",
                                   "url": f"{SITE}/images/apple-touch-icon.png"}},
            "mainEntityOfPage": canonical,
            "inLanguage": "en-US",
        })
        graph.append(breadcrumb([home, ("Insights", f"{SITE}/insights.html"),
                                 (article["headline"], canonical)]))
    else:
        name = PAGE_NAMES.get(rel, h1_of(page) or title.split("|")[0].strip())
        crumbs = [home]
        if rel in SERVICES:
            crumbs.append(("Services", f"{SITE}/services.html"))
            graph.append({"@type": "Service", "name": SERVICES[rel],
                          "serviceType": SERVICES[rel], "description": desc,
                          "url": canonical, "areaServed": "Worldwide",
                          "provider": {"@id": ORG_ID, "@type": "Organization",
                                       "name": "Ciracon"}})
        crumbs.append((name, canonical))
        graph.append({"@type": PAGE_TYPES.get(rel, "WebPage"), "url": canonical,
                      "name": title, "description": desc,
                      "isPartOf": {"@id": f"{SITE}/#website"},
                      "about": {"@id": ORG_ID}})
        graph.append(breadcrumb(crumbs))

    block = "\n  ".join(tags)
    if graph:
        block += "\n  " + jsonld({"@context": "https://schema.org", "@graph": graph}).replace("\n", "\n  ")
    js_flag = "<script>document.documentElement.classList.add('js')</script>"
    return f"<!-- seo:start -->\n  {js_flag}\n  {block}\n  <!-- seo:end -->"


def set_head_block(page, block):
    if "<!-- seo:start -->" in page:
        return re.sub(r"<!-- seo:start -->.*?<!-- seo:end -->", lambda _: block, page, flags=re.S)
    # Insert right after the canonical link (or before </head>)
    m = re.search(r'<link rel="canonical"[^>]*>\n', page)
    if m:
        return page[: m.end()] + "  " + block + "\n" + page[m.end():]
    return page.replace("</head>", f"  {block}\n</head>", 1)


def add_landmarks(page):
    if '<main id="main">' not in page:
        page = re.sub(r"(  </nav>\n)", r'\1\n  <main id="main">\n', page, count=1)
        page = re.sub(r"(\n *<!-- Footer -->|\n *<!-- ═+ Footer ═+ -->|\n  <footer)",
                      lambda m: "\n  </main>\n" + m.group(1), page, count=1)
    if 'class="skip-link"' not in page:
        page = page.replace("<body>\n", '<body>\n  <a class="skip-link" href="#main">Skip to content</a>\n', 1)
    return page


def article_extras(page, rel, slug, info, all_articles):
    # Visible publish date in the article meta row
    pretty = date.fromisoformat(info["date"]).strftime("%B %-d, %Y")
    time_tag = f'<time datetime="{info["date"]}">{pretty}</time>'
    if "<time " not in page:
        page = re.sub(r'(<div class="article-meta">\s*<span>[^<]*</span>)',
                      rf"\1\n        <span>{time_tag}</span>", page, count=1)
    else:
        page = re.sub(r"<time [^>]*>[^<]*</time>", time_tag, page, count=1)

    # CTA + related insights, managed between markers
    svc_page, svc_label = CATEGORY_SERVICE.get(info["category"], ("services.html", "our services"))
    related = [a for a in all_articles if a["category"] == info["category"] and a["slug"] != slug]
    related.sort(key=lambda a: a["date"], reverse=True)
    items = "\n".join(
        f'          <li><a href="insight-{a["slug"]}.html">{esc(a["headline"])}</a></li>'
        for a in related[:4]
    )
    block = f"""<!-- related:start -->
      <aside class="article-cta">
        <h2>Need help with {esc(svc_label)}?</h2>
        <p>Ciracon designs and builds production-grade systems for engineering teams. Learn how we approach <a href="../{svc_page}">{esc(svc_label)}</a>, or <a href="../contact.html">start a conversation</a>.</p>
      </aside>
      <nav class="article-related" aria-label="Related insights">
        <h2>Related insights</h2>
        <ul>
{items}
        </ul>
      </nav>
      <!-- related:end -->"""
    if "<!-- related:start -->" in page:
        page = re.sub(r"<!-- related:start -->.*?<!-- related:end -->", lambda _: block, page, flags=re.S)
    else:
        # Insert before the closing of .article-content (</div> right before </section>)
        page = re.sub(r"(\n    </div>\n  </section>)", lambda m: "\n\n      " + block + m.group(1), page, count=1)
    return page


def collect_articles():
    out = []
    d = os.path.join(REPO_ROOT, "insights")
    for name in sorted(os.listdir(d)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(d, name)
        page = read(path)
        slug = name[len("insight-"):-len(".html")]
        m = re.search(r'<div class="article-meta">\s*<span>([^<]*)</span>', page)
        category = html.unescape(m.group(1)) if m else "AI Engineering"
        out.append({
            "slug": slug, "path": path, "rel": f"insights/{name}",
            "headline": h1_of(page) or title_of(page).split(" | ")[0],
            "category": category,
            "date": article_date(slug, path),
            "modified": git_date(path),
        })
    for a in out:
        if a["modified"] < a["date"]:
            a["modified"] = a["date"]
    return out


def html_pages():
    for name in sorted(os.listdir(REPO_ROOT)):
        if name.endswith(".html"):
            yield name, os.path.join(REPO_ROOT, name)


def canonical_of(page, rel):
    m = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    if m:
        return m.group(1)
    return f"{SITE}/" if rel == "index.html" else f"{SITE}/{rel}"


def main():
    articles = collect_articles()
    sitemap = []

    for rel, path in html_pages():
        page = read(path)
        if 'http-equiv="refresh"' in page:
            continue  # redirect stubs
        canonical = canonical_of(page, rel)
        page = set_head_block(page, build_head_block(rel, page, canonical))
        page = add_landmarks(page)
        write(path, page)
        if rel not in EXCLUDE:
            sitemap.append((canonical, git_date(path)))

    for a in articles:
        page = read(a["path"])
        canonical = canonical_of(page, a["rel"])
        page = set_head_block(page, build_head_block(a["rel"], page, canonical, article=a))
        page = add_landmarks(page)
        page = article_extras(page, a["rel"], a["slug"], a, articles)
        write(a["path"], page)
        sitemap.append((canonical, a["modified"]))

    def prio(u):
        return 0 if u == f"{SITE}/" else (2 if "/insights/" in u else 1)

    sitemap.sort(key=lambda x: (prio(x[0]), x[0]))
    urls = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{d}</lastmod>\n  </url>" for u, d in sitemap
    )
    write(os.path.join(REPO_ROOT, "sitemap.xml"),
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{urls}\n</urlset>\n")
    print(f"Updated {len(sitemap)} pages; wrote sitemap.xml")


if __name__ == "__main__":
    main()
