# Jekyll Include Files for AgentWeave SDK Documentation

This directory contains production-ready Jekyll include files for the AgentWeave SDK documentation site.

## Files Created

### 1. **head.html** (86 lines)
HTML head section with comprehensive SEO, social media, and performance optimizations.

**Features:**
- Complete SEO meta tags (description, keywords, author, robots)
- Open Graph tags for social media sharing
- Twitter Card tags
- Canonical URLs
- Favicon support (multiple sizes)
- Google Fonts preconnect for performance
- Theme color meta tags for dark/light mode
- JSON-LD structured data for search engines
- RSS feed support

**Usage:**
```html
<!DOCTYPE html>
<html>
  {% include head.html %}
  <body>
    <!-- page content -->
  </body>
</html>
```

### 2. **header.html** (89 lines)
Site header with logo, version selector, search, and navigation.

**Features:**
- AgentWeave logo and wordmark
- Version selector dropdown with support for multiple versions
- Client-side search input with keyboard shortcut hint (⌘K)
- Header navigation links
- GitHub repository link
- Dark mode toggle button
- Mobile menu toggle
- Responsive design

**Usage:**
```html
<body>
  {% include header.html %}
  <!-- main content -->
</body>
```

### 3. **footer.html** (120 lines)
Site footer with links, copyright, and metadata.

**Features:**
- Four-column footer grid layout
- About section with tagline
- Documentation links
- Resources links
- Community links with external link icons
- Copyright notice
- Last updated date (from page frontmatter)
- Built with Jekyll badge
- Back to top button
- Support for extra JavaScript files

**Usage:**
```html
<body>
  <!-- main content -->
  {% include footer.html %}
</body>
```

### 4. **nav.html** (212 lines)
Main documentation navigation with collapsible sections.

**Features:**
- Responsive collapsible navigation
- 9 major sections with icons:
  - Getting Started (5 pages)
  - Core Concepts (7 pages)
  - Tutorials (7 pages)
  - How-To Guides (7 pages)
  - API Reference (11 pages)
  - Examples (8 pages)
  - Deployment (7 pages)
  - Security (5 pages)
  - Troubleshooting (5 pages)
- Active state highlighting
- Expandable/collapsible sections with aria attributes
- Mobile-friendly with close button
- SVG icons for each section

**Usage:**
```html
<div class="layout">
  {% include nav.html %}
  <main>
    <!-- page content -->
  </main>
</div>
```

### 5. **sidebar.html** (69 lines)
Page sidebar with table of contents and metadata.

**Features:**
- Auto-generated table of contents
- Sticky positioning
- "Edit this page" link to GitHub
- "Report an issue" link
- Page metadata (last updated, author)
- Responsive design

**Usage:**
```html
<div class="content-layout">
  <article>
    <!-- page content -->
  </article>
  {% include sidebar.html %}
</div>
```

### 6. **toc.html** (141 lines)
Table of contents generator (allejo/jekyll-toc v1.2.0).

**Features:**
- Automatically generates TOC from page headers
- Configurable min/max header levels (h2-h4 by default)
- Ordered or unordered lists
- Smooth scroll support
- Skip headers with `no_toc` class
- Custom CSS classes for styling

**Usage:**
```html
{% include toc.html html=content h_min=2 h_max=4 %}
```

**Parameters:**
- `html` (required): Page content to parse
- `h_min` (optional): Minimum header level (default: 1)
- `h_max` (optional): Maximum header level (default: 6)
- `class` (optional): CSS class for TOC
- `sanitize` (optional): Strip HTML from headers (default: false)
- `ordered` (optional): Use ordered list (default: false)

### 7. **code-block.html** (103 lines)
Enhanced code blocks with syntax highlighting and copy button.

**Features:**
- Language indicator with icons
- Copy to clipboard button
- Optional filename display
- Optional line numbers
- Language-specific icons (Python, JavaScript, TypeScript, Bash, YAML, JSON, Go)
- Syntax highlighting support

**Usage:**
```liquid
{% capture code_example %}
def hello_world():
    print("Hello, World!")
{% endcapture %}

{% include code-block.html
   language="python"
   filename="hello.py"
   line_numbers=true
   code=code_example
%}
```

**Parameters:**
- `language` (required): Programming language
- `code` (required): Code content
- `filename` (optional): Display filename
- `line_numbers` (optional): Show line numbers (default: false)
- `highlight_lines` (optional): Lines to highlight

### 8. **callout.html** (83 lines)
Callout boxes for important information.

**Features:**
- 5 callout types with icons:
  - `info` (blue) - General information
  - `warning` (yellow) - Warning messages
  - `danger` (red) - Danger/error messages
  - `success` (green) - Success messages
  - `tip` (light blue) - Tips and hints
- Optional title
- Markdown support in content
- Accessible with proper roles

**Usage:**
```liquid
{% include callout.html
   type="warning"
   title="Important Note"
   content="This is a warning message with **markdown** support."
%}
```

**Parameters:**
- `type` (optional): Callout type (default: "info")
- `title` (optional): Callout title
- `content` (required): Callout content (supports Markdown)
- `icon` (optional): Show icon (default: true)

### 9. **breadcrumbs.html** (73 lines)
Breadcrumb navigation for page location.

**Features:**
- Auto-generated from page URL
- Home icon
- Schema.org structured data
- Proper separators
- Active page styling
- Cleans up index pages and file extensions

**Usage:**
```html
<div class="page-header">
  {% include breadcrumbs.html %}
</div>
```

### 10. **prev-next.html** (77 lines)
Previous/Next page navigation.

**Features:**
- Links to previous and next pages in documentation
- Page titles and descriptions
- Directional arrows
- Placeholder for missing links
- Responsive design

**Usage:**
```html
<article>
  <!-- page content -->
</article>
{% include prev-next.html %}
```

## Implementation Notes

### Required Site Configuration

Add to your `_config.yml`:

```yaml
# Site settings
title: "AgentWeave SDK"
tagline: "Build secure, cross-cloud AI agents"
description: "Build secure, cross-cloud AI agents with cryptographic identity and automatic authorization"
author: "AgentWeave Team"
version: "0.1.0"
license: "Apache 2.0"

# URLs
url: "https://agentweave.github.io"
baseurl: "/hvs-agent"
github_url: "https://github.com/aj-geddes/agentweave"
pypi_url: "https://pypi.org/project/agentweave/"

# Optional: Previous versions for version selector
previous_versions:
  - number: "0.0.9"
    url: "/v0.0.9/"
    stable: true
```

### CSS Classes to Style

The include files use semantic CSS classes that you'll need to style:

- **Header**: `.site-header`, `.header-container`, `.logo-link`, `.version-selector`, `.search-container`, `.theme-toggle`
- **Navigation**: `.main-nav`, `.nav-section`, `.nav-section-toggle`, `.nav-submenu`, `.nav-link`
- **Footer**: `.site-footer`, `.footer-grid`, `.footer-section`, `.back-to-top`
- **Sidebar**: `.page-sidebar`, `.sidebar-toc`, `.edit-link`, `.report-link`
- **Code**: `.code-block-wrapper`, `.code-copy-button`, `.highlight`
- **Callouts**: `.callout`, `.callout-info`, `.callout-warning`, `.callout-danger`, `.callout-success`, `.callout-tip`
- **Breadcrumbs**: `.breadcrumbs`, `.breadcrumb-list`, `.breadcrumb-item`
- **Prev/Next**: `.prev-next-nav`, `.prev-link`, `.next-link`

### JavaScript Requirements

Some features require JavaScript:

1. **Search** - Client-side search implementation
2. **Theme Toggle** - Dark mode switcher
3. **Copy Button** - Code block copy functionality
4. **Mobile Menu** - Navigation toggle
5. **Version Selector** - Dropdown functionality
6. **Back to Top** - Smooth scroll to top

Create `/assets/js/main.js` to implement these features.

## Directory Structure

```
docs/
├── _includes/
│   ├── head.html
│   ├── header.html
│   ├── footer.html
│   ├── nav.html
│   ├── sidebar.html
│   ├── toc.html
│   ├── code-block.html
│   ├── callout.html
│   ├── breadcrumbs.html
│   ├── prev-next.html
│   └── README.md (this file)
├── _layouts/
│   └── default.html (create this)
├── assets/
│   ├── css/
│   │   └── main.css (create this)
│   ├── js/
│   │   └── main.js (create this)
│   └── images/
│       └── logo.svg
└── _config.yml
```

## Example Layout

Create `_layouts/default.html`:

```html
<!DOCTYPE html>
<html lang="en">
  {% include head.html %}
  <body>
    {% include header.html %}
    
    <div class="page-layout">
      {% include nav.html %}
      
      <main class="page-content">
        <div class="content-wrapper">
          {% include breadcrumbs.html %}
          
          <article class="page-article">
            {{ content }}
          </article>
          
          {% include prev-next.html %}
        </div>
        
        {% include sidebar.html %}
      </main>
    </div>
    
    {% include footer.html %}
  </body>
</html>
```

## License

These templates are part of the AgentWeave SDK project and are licensed under the Apache 2.0 License.

## Credits

- Table of Contents generator based on [allejo/jekyll-toc](https://github.com/allejo/jekyll-toc)
- Icons: Inline SVG from various sources
