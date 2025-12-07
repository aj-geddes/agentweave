# AgentWeave SDK Documentation - Styling System

## Overview

A comprehensive, production-ready CSS/Sass styling system for the AgentWeave SDK documentation. Built with modern best practices, accessibility, and developer experience in mind.

## Quick Stats

- **Total Lines of Sass**: ~3,900 lines
- **Sass Partials**: 6 modular files
- **Components**: 20+ reusable UI components
- **Utility Classes**: 200+ utility classes
- **Color Palette**: 40+ semantic colors with dark mode support
- **Breakpoints**: 6 responsive breakpoints
- **Documentation**: 3 comprehensive guides

## File Structure

```
docs/
├── _sass/                           # Sass Partials (~3,500 lines)
│   ├── _variables.scss              # Design tokens (350 lines)
│   ├── _base.scss                   # Base styles (639 lines)
│   ├── _layout.scss                 # Layout system (735 lines)
│   ├── _components.scss             # UI components (969 lines)
│   ├── _utilities.scss              # Utility classes (553 lines)
│   ├── QUICK_REFERENCE.md           # Developer quick reference
│   └── SAMPLE_TEMPLATE.html         # Full page example
│
├── assets/css/
│   ├── main.scss                    # Main stylesheet (439 lines)
│   └── README.md                    # Architecture documentation
│
└── STYLING_SYSTEM.md                # This file
```

## Design System

### Color Palette

**Light Mode:**
- Primary: #1a365d (Deep Blue) - Trust, security, professionalism
- Accent: #0d9488 (Teal) - Actions, highlights, calls-to-action
- Text: #111827, #374151, #4b5563 (Dark grays)
- Background: #f9fafb, #ffffff, #f3f4f6 (Light grays)

**Dark Mode:**
- Primary: #0ea5e9 (Light Blue)
- Accent: #14b8a6 (Light Teal)
- Text: #e6edf3, #9ca3af, #6b7280 (Light grays)
- Background: #0d1117, #161b22, #1f2937 (Dark grays)

**Semantic Colors:**
- Success: #10b981 (Green)
- Warning: #f59e0b (Orange)
- Danger: #ef4444 (Red)
- Info: #3b82f6 (Blue)

### Typography

**Font Families:**
- Base: System font stack (San Francisco, Segoe UI, Roboto, etc.)
- Monospace: SF Mono, Monaco, Fira Code, Consolas

**Type Scale:** Major Third (1.250 ratio)
- xs: 12px, sm: 14px, base: 16px, md: 18px, lg: 20px
- xl: 24px, 2xl: 30px, 3xl: 36px, 4xl: 48px

**Font Weights:**
- Light (300), Normal (400), Medium (500)
- Semibold (600), Bold (700), Extrabold (800)

### Spacing System

**8px Base Grid:**
```
1 (4px)   2 (8px)   3 (12px)  4 (16px)  5 (20px)  6 (24px)
8 (32px)  10 (40px) 12 (48px) 16 (64px) 20 (80px) 24 (96px)
```

### Breakpoints

**Mobile-First:**
```
xs:  480px  (Small phones)
sm:  640px  (Large phones)
md:  768px  (Tablets)
lg:  1024px (Laptops)
xl:  1280px (Desktops)
2xl: 1536px (Large desktops)
```

## Components

### Layout Components
1. **Header** - Sticky navigation with logo, nav, search, theme toggle
2. **Sidebar** - Collapsible navigation (mobile drawer, desktop sticky)
3. **Main Content** - Responsive content area with max-width
4. **Table of Contents** - Right sidebar on large screens
5. **Footer** - Multi-column footer with links
6. **Grid System** - 1-4 column responsive grids
7. **Breadcrumbs** - Navigation trail
8. **Content Navigation** - Previous/Next links

### UI Components
1. **Buttons** - 5 variants (primary, secondary, accent, outline, ghost)
2. **Callout Boxes** - 6 types (info, warning, danger, success, note, tip)
3. **Cards** - Multiple variants (standard, feature, clickable)
4. **Code Blocks** - Syntax highlighting, copy button, line numbers
5. **Tables** - Responsive, striped, bordered, compact variants
6. **Badges** - Status indicators, color-coded
7. **Tags** - Clickable tags with icons
8. **Search Box** - Search input with results dropdown
9. **API Endpoints** - HTTP method display, parameters
10. **Tabs** - Tabbed content containers
11. **Accordion** - Collapsible sections
12. **Progress Bar** - Loading indicators

### Code Highlighting
- Prism.js compatible syntax highlighting
- Custom color scheme for dark/light modes
- Copy-to-clipboard functionality
- Language labels and file names
- Line number support
- Highlighted lines

## Features

### Accessibility
- WCAG AA compliant color contrast
- Keyboard navigation support (focus-visible)
- Screen reader utilities (sr-only class)
- Skip to content link
- Semantic HTML structure
- ARIA labels where needed
- High contrast mode support
- Reduced motion support

### Dark Mode
- Automatic detection via `prefers-color-scheme`
- Manual override with `data-theme` attribute
- Smooth transitions between themes
- All components support both modes
- CSS custom properties for dynamic switching

### Responsive Design
- Mobile-first approach
- 6 breakpoint system
- Responsive utility classes (d-sm-*, d-md-*, d-lg-*)
- Flexible grid system
- Collapsible navigation
- Touch-friendly targets (44px minimum)

### Performance
- Modular Sass architecture
- Minimal CSS output
- Efficient selectors
- Production-ready (minified)
- No unused CSS
- Fast render times

### Developer Experience
- 200+ utility classes for rapid development
- Comprehensive documentation
- Quick reference guide
- Sample template
- Clear naming conventions
- BEM-like methodology
- Extensive comments

## Usage

### Installation

1. **Jekyll Setup** (if using Jekyll):
```yaml
# _config.yml
sass:
  sass_dir: _sass
  style: compressed
```

2. **Include Stylesheet**:
```html
<link rel="stylesheet" href="/assets/css/main.css">
```

3. **Optional: Syntax Highlighting**:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
```

### Basic Page Structure

```html
<div class="site-wrapper">
  <header class="site-header">
    <!-- Header content -->
  </header>

  <div class="site-container">
    <aside class="sidebar">
      <!-- Sidebar navigation -->
    </aside>

    <main class="main-content">
      <article class="content-wrapper">
        <!-- Your documentation content -->
      </article>
    </main>

    <aside class="toc-wrapper">
      <!-- Table of contents -->
    </aside>
  </div>

  <footer class="site-footer">
    <!-- Footer content -->
  </footer>
</div>
```

### Theme Toggle (JavaScript)

```javascript
const themeToggle = document.querySelector('.theme-toggle');
const html = document.documentElement;

themeToggle.addEventListener('click', () => {
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
});

// Load saved theme
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
  html.setAttribute('data-theme', savedTheme);
}
```

## Common Patterns

### Documentation Page

```html
<main class="main-content">
  <article class="content-wrapper">
    <!-- Breadcrumbs -->
    <nav class="breadcrumbs">
      <a href="/">Home</a>
      <span class="separator"></span>
      <span class="current">Page</span>
    </nav>

    <!-- Page header -->
    <header class="page-header">
      <h1 class="page-title">Page Title</h1>
      <p class="page-description">Description</p>
    </header>

    <!-- Content sections -->
    <section>
      <h2>Section Title</h2>
      <p>Content...</p>
    </section>

    <!-- Navigation -->
    <nav class="content-navigation">
      <a href="/prev" class="nav-link nav-prev">
        <span class="nav-direction">Previous</span>
        <span class="nav-title">Previous Page</span>
      </a>
      <a href="/next" class="nav-link nav-next">
        <span class="nav-direction">Next</span>
        <span class="nav-title">Next Page</span>
      </a>
    </nav>
  </article>
</main>
```

### Callout Boxes

```html
<div class="callout callout-warning">
  <div class="callout-title">Warning</div>
  <p>Important warning message here.</p>
</div>
```

### Code Block

```html
<div class="code-block has-header">
  <div class="code-header">
    <span class="code-language">Python</span>
    <span class="code-filename">example.py</span>
  </div>
  <button class="copy-code-btn">Copy</button>
  <pre><code class="language-python">
def hello():
    print("Hello, World!")
  </code></pre>
</div>
```

### Feature Grid

```html
<div class="grid grid-cols-3 gap-6">
  <div class="card card-feature">
    <div class="card-icon">🔒</div>
    <h3 class="card-title">Secure</h3>
    <p>Built with security first</p>
  </div>
  <!-- More cards... -->
</div>
```

## Documentation

### Quick Reference
See `/docs/_sass/QUICK_REFERENCE.md` for:
- Color tokens
- Typography classes
- Spacing utilities
- Component examples
- Common patterns

### Architecture Guide
See `/docs/assets/css/README.md` for:
- File structure
- Design principles
- Component documentation
- Integration guide
- Browser support

### Sample Template
See `/docs/_sass/SAMPLE_TEMPLATE.html` for:
- Complete HTML example
- All components in use
- JavaScript interactions
- Best practices

## Customization

### Changing Colors

Edit `/docs/_sass/_variables.scss`:

```scss
// Primary color
$color-primary-900: #1a365d; // Change this

// Accent color
$color-accent-600: #0d9488; // Change this
```

### Adding Components

Add to `/docs/_sass/_components.scss`:

```scss
.my-component {
  // Your styles here
  padding: $spacing-4;
  background-color: var(--color-bg-secondary);
  border-radius: $border-radius-md;
}
```

### Creating Utility Classes

Add to `/docs/_sass/_utilities.scss`:

```scss
.my-utility {
  property: value !important;
}
```

## Browser Support

- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

**Required Features:**
- CSS Grid
- CSS Flexbox
- CSS Custom Properties
- CSS `prefers-color-scheme`
- CSS `prefers-reduced-motion`

## Contributing

When adding new styles:

1. Use existing design tokens (variables)
2. Follow BEM-like naming conventions
3. Support both light and dark modes
4. Test responsive behavior
5. Ensure accessibility compliance
6. Add documentation
7. Update quick reference guide

## Best Practices

1. **Use CSS Custom Properties** for runtime-changeable values
2. **Use Sass Variables** for compile-time constants
3. **Mobile-First** - start with mobile styles, enhance for desktop
4. **Utility Classes** for one-off adjustments
5. **Component Classes** for reusable patterns
6. **Semantic HTML** for better accessibility
7. **Test Dark Mode** - always test both themes
8. **Keyboard Navigation** - ensure all interactive elements are keyboard accessible

## Examples

### Complete Documentation Page
See `_sass/SAMPLE_TEMPLATE.html` for a fully working example with:
- Header with navigation
- Sidebar with nested navigation
- Main content with all components
- Table of contents
- Footer
- JavaScript interactions
- Theme toggle
- Mobile menu
- Copy code functionality

### Component Gallery
The sample template demonstrates:
- Callout boxes (info, warning, danger, success)
- Code blocks with syntax highlighting
- API endpoint documentation
- Feature cards in a grid
- Buttons in various styles
- Navigation components
- Typography hierarchy

## Production Checklist

Before deploying:

- [ ] Compile Sass to CSS
- [ ] Minify CSS for production
- [ ] Test on multiple browsers
- [ ] Test dark mode
- [ ] Test mobile responsiveness
- [ ] Validate accessibility (WCAG AA)
- [ ] Test keyboard navigation
- [ ] Check print styles
- [ ] Verify all links work
- [ ] Test with screen readers

## Support

For questions or issues:
- Check `/docs/assets/css/README.md` for architecture details
- Review `/docs/_sass/QUICK_REFERENCE.md` for usage examples
- Examine `/docs/_sass/SAMPLE_TEMPLATE.html` for complete examples
- Review component code in `_sass/_components.scss`

## License

Part of the AgentWeave SDK documentation project.

---

**Built with**: Sass, CSS Custom Properties, Modern CSS
**Compatible with**: Jekyll, static site generators
**Last Updated**: December 7, 2025
