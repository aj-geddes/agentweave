# Jekyll Site Setup - Complete

This document describes the complete Jekyll site structure created for AgentWeave SDK documentation.

## Files Created

### Core Configuration

1. **Gemfile** - Ruby dependencies including:
   - `github-pages` gem for GitHub Pages compatibility
   - `jekyll-seo-tag` for SEO metadata
   - `jekyll-sitemap` for sitemap generation
   - `jekyll-feed` for RSS feed
   - `jekyll-redirect-from` for URL redirects
   - `webrick` for local development server

2. **_config.yml** - Main Jekyll configuration with:
   - Site metadata (title, description, author)
   - URL settings for GitHub Pages deployment
   - Markdown and syntax highlighting configuration
   - Collections for tutorials, guides, examples, API docs
   - Complete navigation structure
   - SEO settings (Twitter cards, Open Graph)
   - Plugin configuration

3. **robots.txt** - Search engine crawler instructions

4. **.gitignore** - Excludes Jekyll build artifacts and dependencies

## Directory Structure

### Layouts (`_layouts/`)

- **default.html** - Base layout with header, nav, content, sidebar, footer
- **page.html** - Standard documentation page with breadcrumbs, metadata, prev/next navigation
- **tutorial.html** - Tutorial-specific layout with progress tracking, objectives, prerequisites
- **api.html** - API reference layout with syntax highlighting, parameter tables, examples

### Includes (`_includes/`)

- **head.html** - HTML head with SEO meta tags, stylesheets, fonts, dark mode script
- **header.html** - Site header with logo, main nav, search, theme toggle, GitHub link
- **footer.html** - Footer with documentation links, resources, community, copyright
- **nav.html** - Comprehensive sidebar navigation for all documentation sections
- **sidebar.html** - Right sidebar with table of contents, related links, quick links
- **toc.html** - Table of contents generator (from jekyll-toc)

### Stylesheets

#### CSS (`assets/css/`)
- **main.css** - Main stylesheet with:
  - CSS variables for light/dark themes
  - Typography system
  - Layout components (header, nav, sidebar, footer)
  - Responsive design (mobile, tablet, desktop)
  - Utility classes

- **syntax.css** - Code syntax highlighting (GitHub-style):
  - Light mode theme
  - Dark mode theme
  - Support for multiple languages

#### SASS (`_sass/`)
- **_variables.scss** - Design tokens:
  - Color palette
  - Typography scale
  - Spacing system
  - Layout dimensions
  - Border radius values
  - Shadow definitions
  - Z-index layers
  - Responsive breakpoints

- **_mixins.scss** - Reusable SASS mixins:
  - Responsive breakpoint helpers
  - Flexbox utilities
  - Typography mixins
  - Button styles
  - Card components
  - Focus states
  - Accessibility helpers

### JavaScript (`assets/js/`)

- **main.js** - Core functionality:
  - Theme management (light/dark mode toggle)
  - Mobile menu functionality
  - Search integration placeholder
  - Code block copy buttons
  - Language labels for code blocks
  - Smooth scroll for anchor links
  - Active navigation highlighting
  - External link handling
  - Accessibility enhancements

## Navigation Structure

The site includes comprehensive navigation for:

1. **Getting Started**
   - Introduction
   - Installation
   - Quick Start
   - Configuration

2. **Core Concepts**
   - Agent Identity (SPIFFE)
   - Authorization (OPA)
   - A2A Protocol
   - mTLS Transport
   - Agent Cards
   - Context Management
   - Observability

3. **Tutorials**
   - Your First Agent
   - Multi-Agent System
   - Custom Authorization
   - Cross-Cloud Deployment
   - Tool Integration

4. **How-To Guides**
   - Configure Identity
   - Write Authorization Policies
   - Implement Custom Tools
   - Handle Errors
   - Monitor Agents
   - Secure Secrets
   - Rate Limiting
   - Testing Agents

5. **API Reference**
   - Agent
   - Decorators
   - Identity
   - Authorization
   - Transport
   - A2A Protocol
   - Context
   - Configuration
   - Exceptions

6. **Examples**
   - Basic Agent
   - Multi-Agent Chat
   - Research Assistant
   - Code Review Agent
   - Data Pipeline
   - Kubernetes Operator

7. **Deployment**
   - Docker
   - Kubernetes
   - AWS ECS
   - Google Cloud Run
   - Azure Container Apps
   - Helm Charts

8. **Security**
   - Security Model
   - Threat Model
   - Best Practices
   - Compliance
   - Auditing

9. **Troubleshooting**
   - Common Issues
   - Identity Problems
   - Authorization Failures
   - Connection Issues
   - Performance
   - Debugging

## Features

### Built-in Functionality

- **Dark Mode** - Automatic dark/light theme switching with persistence
- **Responsive Design** - Mobile-first design that works on all devices
- **SEO Optimized** - Full meta tags, Open Graph, Twitter Cards
- **Accessibility** - WCAG 2.1 compliant with skip links, ARIA labels
- **Code Highlighting** - GitHub-style syntax highlighting for all languages
- **Copy Buttons** - One-click code copying with visual feedback
- **Table of Contents** - Auto-generated TOC for long pages
- **Breadcrumbs** - Navigation breadcrumbs on all pages
- **Search Ready** - Prepared for Algolia or Lunr.js integration
- **Analytics Ready** - Placeholder for analytics integration

### Collections

The site uses Jekyll collections for organizing content:

- `_tutorials/` - Step-by-step tutorials
- `_guides/` - How-to guides
- `_examples/` - Example code and projects
- `_api/` - API reference documentation

## Local Development

### First Time Setup

```bash
# Install dependencies
bundle install

# Run development server
bundle exec jekyll serve

# Visit http://localhost:4000/agentweave/
```

### Build Commands

```bash
# Development build
bundle exec jekyll build

# Production build
JEKYLL_ENV=production bundle exec jekyll build

# Serve with live reload
bundle exec jekyll serve --livereload

# Serve with drafts
bundle exec jekyll serve --drafts
```

## Deployment

### GitHub Pages

The site is configured for GitHub Pages deployment:

```yaml
url: "https://aj-geddes.github.io"
baseurl: "/agentweave"
```

**Deployment Steps:**
1. Push to `main` branch
2. GitHub Actions builds the site automatically
3. Site published to `https://aj-geddes.github.io/agentweave/`

### Custom Domain

To use a custom domain:

1. Update `_config.yml`:
```yaml
url: "https://docs.agentweave.dev"
baseurl: ""
```

2. Add CNAME file:
```
docs.agentweave.dev
```

3. Configure DNS with GitHub Pages IP addresses

## Content Guidelines

### Writing Documentation

All markdown files should include front matter:

```yaml
---
layout: page
title: Page Title
description: Brief description for SEO
---
```

### Code Blocks

Use fenced code blocks with language specification:

```python
from hvs_agent import Agent

agent = Agent(name="my-agent")
```

### Admonitions

Use HTML for callouts:

```html
<div class="callout callout-info">
  <strong>Note:</strong> Important information here.
</div>
```

## Customization

### Colors

Edit CSS variables in `assets/css/main.css`:

```css
:root {
  --color-primary: #0066cc;
  --color-secondary: #00a99d;
  /* ... */
}
```

### Navigation

Edit navigation structure in `_config.yml`:

```yaml
navigation:
  main:
    - title: "Section Name"
      url: /section/
      children:
        - title: "Page Name"
          url: /section/page/
```

### Typography

Modify font families in `_sass/_variables.scss`:

```scss
$font-family-base: 'Inter', sans-serif;
$font-family-mono: 'JetBrains Mono', monospace;
```

## Maintenance

### Updating Dependencies

```bash
bundle update
```

### Checking for Broken Links

```bash
bundle exec jekyll build
bundle exec htmlproofer ./_site
```

### Performance Testing

Use Lighthouse or PageSpeed Insights to audit:
- https://pagespeed.web.dev/

## Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Liquid Template Language](https://shopify.github.io/liquid/)
- [kramdown Syntax](https://kramdown.gettalong.org/syntax.html)
