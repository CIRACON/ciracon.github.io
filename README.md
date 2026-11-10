# CIRACON Public Website

This repository hosts the CIRACON public website at [https://www.ciracon.com](https://www.ciracon.com).

## About

CIRACON provides engineering-first consulting in AI engineering, platform engineering, DevOps automation, and cloud infrastructure. This website serves as our public-facing presence, showcasing our services and expertise.

## Structure

- Static HTML/CSS/JS served by GitHub Pages at `www.ciracon.com` (behind Cloudflare).
- `insights/` holds article pages. New articles are generated from Markdown in `articles/`
  by `.github/workflows/generate-article.yml` (manual trigger), which opens a PR for review.

## SEO

`scripts/seo_build.py` is idempotent and should be run after adding or editing pages:

```bash
python scripts/seo_build.py
```

It manages the block between `<!-- seo:start -->` / `<!-- seo:end -->` in each page's `<head>`
(Open Graph, Twitter cards, JSON-LD structured data), adds publish dates, a service CTA and
related links to insight articles (`<!-- related:start -->` / `<!-- related:end -->`), and
regenerates `sitemap.xml`. Edit titles and meta descriptions directly in each page; the script
reads them from there. The article workflow runs it automatically.

Other SEO files: `robots.txt` (points to the sitemap; Cloudflare prepends its managed rules),
`404.html`, and `images/og-default.png` (default social share image).

## License

Copyright © CIRACON. All rights reserved.