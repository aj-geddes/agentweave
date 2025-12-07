# AgentWeave SDK Documentation - CSS Architecture

This directory contains the CSS/Sass styling system for the AgentWeave SDK documentation site.

## File Structure

```
docs/
├── _sass/                      # Sass partials (imported by main.scss)
│   ├── _variables.scss        # CSS custom properties and Sass variables
│   ├── _base.scss             # Base styles and resets
│   ├── _layout.scss           # Layout components (header, sidebar, footer)
│   ├── _components.scss       # Reusable UI components
│   └── _utilities.scss        # Utility classes
│
└── assets/css/
    └── main.scss              # Main stylesheet (imports all partials)
```

## Architecture Overview

### 1. **_variables.scss**
Defines the design system foundation:
- **Color Palette**: Deep blue primary (#1a365d), teal accent (#0d9488)
- **Typography**: System font stack + monospace for code
- **Spacing System**: Based on 8px grid (4px, 8px, 16px, 24px, etc.)
- **Breakpoints**: Mobile-first responsive (480px, 640px, 768px, 1024px, 1280px, 1536px)
- **Dark Mode**: CSS custom properties with `prefers-color-scheme` support
- **Shadows, Borders, Transitions**: Consistent design tokens

### 2. **_base.scss**
Foundation styles:
- CSS reset/normalize
- Typography hierarchy (h1-h6)
- Links, lists, tables
- Code blocks and pre-formatted text
- Forms (basic)
- Scrollbar styling
- Accessibility features (skip links, screen reader utilities)
- Print styles

### 3. **_layout.scss**
Structural layout components:
- **Header**: Sticky navigation with logo, main nav, and actions
- **Sidebar**: Collapsible navigation (fixed on mobile, sticky on desktop)
- **Main Content**: Responsive content area with max-width constraints
- **Footer**: Multi-column footer with links
- **Grid System**: Responsive grid utilities (1-4 columns)
- **Table of Contents**: Right sidebar on larger screens
- **Breadcrumbs**: Navigation trail
- **Content Navigation**: Previous/Next page links

### 4. **_components.scss**
Reusable UI components:

#### Buttons
- Variants: primary, secondary, accent, outline, ghost
- Sizes: sm, base, lg
- States: hover, focus, disabled

#### Code Blocks
- Syntax highlighting (Prism.js compatible)
- Copy code button
- Line numbers support
- Language labels
- Highlighted lines

#### Callout Boxes
- Types: info, warning, danger, success, note, tip
- Color-coded with icons
- Semantic styling

#### Cards
- Header, body, footer structure
- Clickable card variant
- Feature card variant

#### Tables
- Responsive wrapper
- Variants: striped, bordered, compact
- Hover states

#### Badges & Tags
- Status indicators
- Color variants
- Outline style

#### Search Box
- Search input with icon
- Results dropdown
- Keyboard navigation support

#### API Reference Components
- Endpoint display (HTTP method + path)
- Parameter documentation
- Method color coding (GET, POST, PUT, DELETE, PATCH)

#### Additional Components
- Tabs
- Accordion/Collapsible
- Progress bar

### 5. **_utilities.scss**
Utility classes for rapid development:
- **Spacing**: Margin and padding (m-, mt-, mb-, ml-, mr-, mx-, my-, p-, pt-, etc.)
- **Text**: Alignment, transform, weight, size, color, overflow
- **Display**: Block, flex, grid, inline, none (with responsive variants)
- **Flexbox**: Direction, wrap, justify, align, gap
- **Width/Height**: Auto, full, percentages, viewport units
- **Position**: Static, relative, absolute, fixed, sticky
- **Borders**: Border and border-radius utilities
- **Background**: Background color utilities
- **Shadows**: Box shadow utilities
- **Cursor**: Cursor type utilities
- **Opacity**: Opacity levels
- **Z-index**: Layering utilities
- **Transitions**: Animation utilities

## Design Principles

### 1. **Mobile-First Responsive Design**
All layouts are designed mobile-first, progressively enhanced for larger screens:
```scss
// Base styles for mobile
.element { padding: 1rem; }

// Enhanced for tablet
@media (min-width: $breakpoint-md) {
  .element { padding: 2rem; }
}
```

### 2. **Dark Mode Support**
CSS custom properties enable seamless theme switching:
- Automatic detection via `prefers-color-scheme`
- Manual override with `data-theme="dark"` or `data-theme="light"`
- All components use CSS variables for colors

### 3. **High Contrast & Accessibility**
- WCAG AA compliant color contrasts
- Focus indicators for keyboard navigation
- Screen reader utilities (`.sr-only`)
- Skip to content link
- Reduced motion support (`prefers-reduced-motion`)
- High contrast mode support (`prefers-contrast: high`)

### 4. **Performance**
- Minimal CSS with utility classes
- Efficient selectors
- Optimized for production with minification
- No unused CSS

### 5. **Consistency**
- Design tokens for all values (no magic numbers)
- Systematic spacing scale
- Typography scale
- Color palette
- Component patterns

## Color Palette

### Light Mode
- **Primary**: #1a365d (Deep Blue) - Security, trust, professionalism
- **Accent**: #0d9488 (Teal) - Actions, highlights, interactive elements
- **Text**:
  - Primary: #111827 (Near black)
  - Secondary: #374151 (Medium gray)
  - Tertiary: #4b5563 (Light gray)
- **Background**:
  - Primary: #f9fafb (Very light gray)
  - Secondary: #ffffff (White)
  - Tertiary: #f3f4f6 (Light gray)

### Dark Mode
- **Primary**: #0ea5e9 (Light Blue)
- **Accent**: #14b8a6 (Light Teal)
- **Text**:
  - Primary: #e6edf3 (Off white)
  - Secondary: #9ca3af (Medium gray)
  - Tertiary: #6b7280 (Dark gray)
- **Background**:
  - Primary: #0d1117 (Near black)
  - Secondary: #161b22 (Dark gray)
  - Tertiary: #1f2937 (Medium dark)

### Semantic Colors
- **Success**: #10b981 (Green)
- **Warning**: #f59e0b (Orange)
- **Danger**: #ef4444 (Red)
- **Info**: #3b82f6 (Blue)

## Typography Scale

Major Third scale (1.250 ratio):
- **xs**: 0.75rem (12px)
- **sm**: 0.875rem (14px)
- **base**: 1rem (16px)
- **md**: 1.125rem (18px)
- **lg**: 1.25rem (20px)
- **xl**: 1.5rem (24px)
- **2xl**: 1.875rem (30px)
- **3xl**: 2.25rem (36px)
- **4xl**: 3rem (48px)

## Spacing System

8px base grid:
- **1**: 0.25rem (4px)
- **2**: 0.5rem (8px)
- **3**: 0.75rem (12px)
- **4**: 1rem (16px)
- **5**: 1.25rem (20px)
- **6**: 1.5rem (24px)
- **8**: 2rem (32px)
- **10**: 2.5rem (40px)
- **12**: 3rem (48px)
- **16**: 4rem (64px)

## Breakpoints

Mobile-first breakpoints:
- **xs**: 480px (Small phones)
- **sm**: 640px (Large phones)
- **md**: 768px (Tablets)
- **lg**: 1024px (Laptops)
- **xl**: 1280px (Desktops)
- **2xl**: 1536px (Large desktops)

## Usage Examples

### Basic Page Layout
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
        <!-- Documentation content -->
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

### Callout Box
```html
<div class="callout callout-warning">
  <div class="callout-title">Warning</div>
  <p>This is an important warning message.</p>
</div>
```

### Code Block with Copy Button
```html
<div class="code-block">
  <div class="code-header">
    <span class="code-language">Python</span>
    <span class="code-filename">example.py</span>
  </div>
  <button class="copy-code-btn">Copy</button>
  <pre><code class="language-python">def hello():
    print("Hello, World!")</code></pre>
</div>
```

### API Endpoint
```html
<div class="api-endpoint">
  <div class="endpoint-header">
    <span class="http-method method-post">POST</span>
    <span class="endpoint-path">/api/agents</span>
  </div>
  <p class="endpoint-description">Create a new agent</p>
  <div class="endpoint-section">
    <div class="section-title">Parameters</div>
    <div class="parameter">
      <span class="param-name">name</span>
      <span class="param-type">string</span>
      <span class="param-required">required</span>
      <p class="param-description">The agent name</p>
    </div>
  </div>
</div>
```

### Cards Grid
```html
<div class="grid grid-cols-3">
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Feature 1</h3>
    </div>
    <div class="card-body">
      <p>Feature description</p>
    </div>
  </div>
  <!-- More cards -->
</div>
```

### Utility Classes
```html
<!-- Spacing -->
<div class="mt-8 mb-6 px-4">Content with margins and padding</div>

<!-- Flexbox -->
<div class="d-flex justify-between items-center gap-4">
  <span>Left</span>
  <span>Right</span>
</div>

<!-- Text -->
<p class="text-lg font-semibold text-accent">Highlighted text</p>

<!-- Responsive Display -->
<div class="d-none d-md-block">Visible on medium screens and up</div>
```

## Integration with Jekyll

This stylesheet is designed for Jekyll static site generator:

1. **Jekyll Front Matter**: The `main.scss` file includes Jekyll front matter (`---`) for processing
2. **Sass Import**: Jekyll automatically processes `@import` statements
3. **CSS Variables**: Runtime theme switching without recompilation
4. **Minimal Configuration**: Works out of the box with Jekyll's default Sass processor

### Jekyll Configuration
Add to `_config.yml`:
```yaml
sass:
  sass_dir: _sass
  style: compressed
```

### HTML Head
Include in `<head>`:
```html
<link rel="stylesheet" href="{{ '/assets/css/main.css' | relative_url }}">
```

## Browser Support

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest 2 versions)
- **CSS Features**: CSS Grid, Flexbox, Custom Properties, `prefers-color-scheme`
- **Graceful Degradation**: Fallbacks for older browsers where needed
- **Progressive Enhancement**: Enhanced features for modern browsers

## Contributing

When adding new styles:
1. Use existing design tokens (variables)
2. Follow BEM-like naming conventions
3. Add utility classes to `_utilities.scss`
4. Document new components in this README
5. Test in both light and dark modes
6. Ensure accessibility compliance
7. Test responsive behavior

## License

Part of the AgentWeave SDK documentation project.
