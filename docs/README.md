# AgentWeave SDK Documentation

This directory contains the Jekyll-based documentation site for AgentWeave SDK.

## Local Development

### Prerequisites

- Ruby 2.7 or higher
- Bundler

### Setup

1. Install dependencies:
```bash
bundle install
```

2. Run the development server:
```bash
bundle exec jekyll serve
```

3. Visit `http://localhost:4000/agentweave/` in your browser

### Build for Production

```bash
bundle exec jekyll build
```

The site will be generated in the `_site` directory.

## Project Structure

```
docs/
├── _config.yml              # Jekyll configuration
├── _layouts/                # Page layouts
│   ├── default.html         # Base layout
│   ├── page.html            # Standard page
│   ├── tutorial.html        # Tutorial pages
│   └── api.html             # API documentation
├── _includes/               # Reusable components
│   ├── head.html
│   ├── header.html
│   ├── footer.html
│   ├── nav.html             # Main navigation
│   ├── sidebar.html
│   └── toc.html             # Table of contents
├── _sass/                   # SASS partials
├── assets/
│   ├── css/                 # Compiled CSS
│   ├── js/                  # JavaScript
│   └── images/              # Images and icons
├── _tutorials/              # Tutorial content
├── _guides/                 # How-to guides
├── _examples/               # Example code
├── _api/                    # API reference
├── getting-started/         # Getting started pages
├── concepts/                # Core concepts
├── deployment/              # Deployment guides
├── security/                # Security documentation
├── troubleshooting/         # Troubleshooting guides
└── index.md                 # Home page
```

## Writing Documentation

### Front Matter

All pages should include front matter:

```yaml
---
layout: page
title: Page Title
description: Brief description of the page
---
```

### Tutorials

Tutorials should use the tutorial layout:

```yaml
---
layout: tutorial
title: Tutorial Title
description: What you'll build
difficulty: Beginner|Intermediate|Advanced
duration: 30
learning_objectives:
  - First objective
  - Second objective
prerequisites:
  - name: Python 3.10+
    url: /getting-started/installation/
---
```

### API Documentation

API pages should use the api layout:

```yaml
---
layout: api
title: Agent
module: hvs_agent.agent
description: Core Agent class
import_path: from hvs_agent import Agent
version: 0.1.0
source_file: hvs_agent/agent.py
---
```

## Deployment

This site is configured for GitHub Pages with a custom domain.

### GitHub Pages Setup

1. Push to the `main` branch
2. GitHub Actions will automatically build and deploy
3. Site will be available at `https://aj-geddes.github.io/agentweave/`

### Custom Domain

Configure in `_config.yml`:
```yaml
url: "https://docs.agentweave.dev"
baseurl: ""
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for documentation contribution guidelines.

## License

The documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
