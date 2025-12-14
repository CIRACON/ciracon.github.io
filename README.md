# CIRACON Public Website

<a href="https://github.com/CIRACON/ciracon.github.io/actions/workflows/regenerate.yml"><img src="https://github.com/CIRACON/ciracon.github.io/actions/workflows/regenerate.yml/badge.svg"></a>

This repository hosts the CIRACON public website at [https://ciracon.github.io](https://ciracon.github.io).

## About

CIRACON provides consulting and training solutions specializing in AWS, Azure, Kubernetes, and DevOps. This website serves as our public-facing presence, showcasing our services and expertise.

## Daily Re-design Workflow

The website is uniquely regenerated **daily** using GitHub Actions and AI. This automated workflow:

1. **Runs daily at 10:00 UTC** (2:00 AM Pacific Time) via a scheduled GitHub Actions workflow
2. **Uses GitHub Models API** (GPT-4o-mini) to generate fresh HTML based on instructions
3. **Reads instructions** from `instructions.md` which defines the site requirements, content, and design guidelines
4. **Generates index.html** with a new design variation while maintaining core content
5. **Commits and pushes** the regenerated site back to the repository
6. **Can be triggered manually** via workflow_dispatch for on-demand regeneration

### Workflow Details

- **Workflow file**: `.github/workflows/regenerate.yml`
- **Instructions file**: `instructions.md` - Contains the prompt and requirements for site generation
- **Model**: GPT-4o-mini via GitHub Models API
- **Schedule**: Daily at 10:00 UTC (cron: `0 10 * * *`)
- **Manual trigger**: Available via GitHub Actions UI

The workflow ensures the website stays fresh with modern designs while maintaining consistent branding and content. Each regeneration creates a clean, responsive, and accessible design using modern CSS frameworks like TailwindCSS, Material, or Bootstrap.

### How It Works

1. The workflow checks out the repository
2. Reads the generation instructions from `instructions.md`
3. Sends a prompt to the GitHub Models API with the instructions
4. Receives generated HTML content
5. Writes the content to `index.html`
6. Logs the regeneration timestamp to `regeneration.log`
7. Commits and pushes changes if the site was updated

## License

Copyright © CIRACON. All rights reserved.