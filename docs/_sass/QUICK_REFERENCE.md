# CSS Quick Reference Guide

Quick reference for common styling patterns in the AgentWeave SDK documentation.

## Table of Contents
- [Color Tokens](#color-tokens)
- [Typography](#typography)
- [Spacing](#spacing)
- [Layout Patterns](#layout-patterns)
- [Component Classes](#component-classes)
- [Utility Classes](#utility-classes)

## Color Tokens

### CSS Custom Properties (Use These!)
```css
/* Backgrounds */
--color-bg-primary        /* Main page background */
--color-bg-secondary      /* Card/section backgrounds */
--color-bg-tertiary       /* Subtle backgrounds */
--color-bg-code           /* Code block backgrounds */

/* Text */
--color-text-primary      /* Headings, primary text */
--color-text-secondary    /* Body text */
--color-text-tertiary     /* Muted text, captions */

/* Borders */
--color-border            /* Default borders */
--color-border-hover      /* Hover state borders */

/* Links */
--color-link              /* Link color */
--color-link-hover        /* Link hover color */

/* Branding */
--color-primary           /* Primary brand color */
--color-primary-hover     /* Primary hover state */
--color-accent            /* Accent/action color */
--color-accent-hover      /* Accent hover state */

/* Shadows */
--shadow-sm, --shadow-base, --shadow-md, --shadow-lg
```

### Semantic Colors (Sass Variables)
```scss
$color-success           // #10b981 (Green)
$color-warning           // #f59e0b (Orange)
$color-danger            // #ef4444 (Red)
$color-info              // #3b82f6 (Blue)
```

## Typography

### Headings
```html
<h1>Page Title</h1>          <!-- 36px/48px, extrabold -->
<h2>Major Section</h2>        <!-- 30px/36px, bold, bottom border -->
<h3>Subsection</h3>           <!-- 24px/30px, bold -->
<h4>Minor Heading</h4>        <!-- 20px/24px, bold -->
<h5>Small Heading</h5>        <!-- 18px/20px, bold -->
<h6>Tiny Heading</h6>         <!-- 16px/18px, bold, muted -->
```

### Text Classes
```html
<!-- Size -->
<p class="text-xs">Extra small (12px)</p>
<p class="text-sm">Small (14px)</p>
<p class="text-base">Base (16px) - default</p>
<p class="text-lg">Large (20px)</p>
<p class="text-xl">Extra large (24px)</p>

<!-- Weight -->
<span class="font-light">Light (300)</span>
<span class="font-normal">Normal (400)</span>
<span class="font-medium">Medium (500)</span>
<span class="font-semibold">Semibold (600)</span>
<span class="font-bold">Bold (700)</span>

<!-- Color -->
<span class="text-primary">Primary text color</span>
<span class="text-secondary">Secondary text color</span>
<span class="text-tertiary">Tertiary text color</span>
<span class="text-accent">Accent color</span>

<!-- Alignment -->
<p class="text-left">Left aligned</p>
<p class="text-center">Center aligned</p>
<p class="text-right">Right aligned</p>
```

### Code
```html
<code>inline code</code>
<pre><code>block code</code></pre>
<kbd>Ctrl</kbd> + <kbd>C</kbd>
```

## Spacing

### Scale (8px base)
```
1  = 4px    (0.25rem)
2  = 8px    (0.5rem)
3  = 12px   (0.75rem)
4  = 16px   (1rem)
5  = 20px   (1.25rem)
6  = 24px   (1.5rem)
8  = 32px   (2rem)
10 = 40px   (2.5rem)
12 = 48px   (3rem)
```

### Margin
```html
<!-- All sides -->
<div class="m-4">16px margin all sides</div>

<!-- Individual sides -->
<div class="mt-6">24px top margin</div>
<div class="mb-4">16px bottom margin</div>
<div class="ml-2">8px left margin</div>
<div class="mr-2">8px right margin</div>

<!-- Axis -->
<div class="mx-4">16px horizontal margin (left + right)</div>
<div class="my-6">24px vertical margin (top + bottom)</div>

<!-- Auto -->
<div class="mx-auto">Centered with auto margins</div>
```

### Padding
```html
<!-- Same pattern as margin, but with 'p' prefix -->
<div class="p-6">24px padding all sides</div>
<div class="pt-4 pb-4">16px top and bottom padding</div>
<div class="px-6">24px horizontal padding</div>
<div class="py-3">12px vertical padding</div>
```

## Layout Patterns

### Container
```html
<!-- Full width container with max-width -->
<div class="container">Content</div>

<!-- Narrow content container -->
<div class="container container-narrow">Text content</div>
```

### Grid
```html
<!-- 2 column grid (responsive) -->
<div class="grid grid-cols-2">
  <div>Column 1</div>
  <div>Column 2</div>
</div>

<!-- 3 column grid -->
<div class="grid grid-cols-3">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

### Flexbox
```html
<!-- Basic flex container -->
<div class="d-flex">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

<!-- Common flex patterns -->
<div class="d-flex justify-between items-center">
  <span>Left</span>
  <span>Right</span>
</div>

<div class="d-flex justify-center items-center">
  <span>Centered</span>
</div>

<div class="d-flex flex-col gap-4">
  <div>Stacked</div>
  <div>Items</div>
</div>
```

## Component Classes

### Buttons
```html
<button class="btn btn-primary">Primary Button</button>
<button class="btn btn-secondary">Secondary Button</button>
<button class="btn btn-accent">Accent Button</button>
<button class="btn btn-outline">Outline Button</button>
<button class="btn btn-ghost">Ghost Button</button>

<!-- Sizes -->
<button class="btn btn-primary btn-sm">Small</button>
<button class="btn btn-primary">Normal</button>
<button class="btn btn-primary btn-lg">Large</button>

<!-- Block button -->
<button class="btn btn-primary btn-block">Full Width</button>
```

### Callouts
```html
<div class="callout callout-info">
  <div class="callout-title">Info</div>
  <p>Information message</p>
</div>

<div class="callout callout-warning">
  <div class="callout-title">Warning</div>
  <p>Warning message</p>
</div>

<div class="callout callout-danger">
  <div class="callout-title">Danger</div>
  <p>Danger message</p>
</div>

<div class="callout callout-success">
  <div class="callout-title">Success</div>
  <p>Success message</p>
</div>

<div class="callout callout-note">
  <div class="callout-title">Note</div>
  <p>Note or tip message</p>
</div>
```

### Cards
```html
<!-- Basic card -->
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Card Title</h3>
    <p class="card-subtitle">Subtitle</p>
  </div>
  <div class="card-body">
    <p>Card content</p>
  </div>
  <div class="card-footer">
    Footer content
  </div>
</div>

<!-- Feature card -->
<div class="card card-feature">
  <div class="card-icon">🚀</div>
  <h3 class="card-title">Feature Name</h3>
  <p>Feature description</p>
</div>
```

### Badges
```html
<span class="badge">Default</span>
<span class="badge badge-primary">Primary</span>
<span class="badge badge-accent">Accent</span>
<span class="badge badge-success">Success</span>
<span class="badge badge-warning">Warning</span>
<span class="badge badge-danger">Danger</span>

<!-- API status badges -->
<span class="api-status status-stable">Stable</span>
<span class="api-status status-beta">Beta</span>
<span class="api-status status-experimental">Experimental</span>
<span class="api-status status-deprecated">Deprecated</span>
```

### Code Blocks
```html
<!-- Basic code block -->
<div class="code-block">
  <pre><code class="language-python">
def hello():
    print("Hello, World!")
  </code></pre>
</div>

<!-- Code block with header -->
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

### Tables
```html
<!-- Basic table -->
<table>
  <thead>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Data 1</td>
      <td>Data 2</td>
    </tr>
  </tbody>
</table>

<!-- Responsive table -->
<div class="table-responsive">
  <table>
    <!-- table content -->
  </table>
</div>

<!-- Table variants -->
<table class="table-striped">...</table>
<table class="table-bordered">...</table>
<table class="table-compact">...</table>
```

### API Endpoint
```html
<div class="api-endpoint">
  <div class="endpoint-header">
    <span class="http-method method-get">GET</span>
    <span class="endpoint-path">/api/agents/:id</span>
  </div>
  <p class="endpoint-description">Get agent by ID</p>

  <div class="endpoint-section">
    <div class="section-title">Parameters</div>
    <div class="parameter">
      <span class="param-name">id</span>
      <span class="param-type">string</span>
      <span class="param-required">required</span>
      <p class="param-description">The agent ID</p>
    </div>
  </div>
</div>
```

### Tabs
```html
<div class="tabs">
  <div class="tab-list">
    <button class="tab-button active">Tab 1</button>
    <button class="tab-button">Tab 2</button>
    <button class="tab-button">Tab 3</button>
  </div>
  <div class="tab-content active">
    <p>Content for tab 1</p>
  </div>
  <div class="tab-content">
    <p>Content for tab 2</p>
  </div>
  <div class="tab-content">
    <p>Content for tab 3</p>
  </div>
</div>
```

## Utility Classes

### Display
```html
<div class="d-none">Hidden</div>
<div class="d-block">Block</div>
<div class="d-flex">Flex</div>
<div class="d-grid">Grid</div>

<!-- Responsive display -->
<div class="d-none d-md-block">Hidden on mobile, visible on tablet+</div>
<div class="d-block d-lg-none">Visible on mobile/tablet, hidden on desktop</div>
```

### Flexbox Utilities
```html
<!-- Direction -->
<div class="d-flex flex-row">Horizontal (default)</div>
<div class="d-flex flex-col">Vertical</div>

<!-- Justify content -->
<div class="d-flex justify-start">Start (default)</div>
<div class="d-flex justify-center">Center</div>
<div class="d-flex justify-end">End</div>
<div class="d-flex justify-between">Space between</div>
<div class="d-flex justify-around">Space around</div>

<!-- Align items -->
<div class="d-flex items-start">Top</div>
<div class="d-flex items-center">Center</div>
<div class="d-flex items-end">Bottom</div>
<div class="d-flex items-stretch">Stretch (default)</div>

<!-- Gap -->
<div class="d-flex gap-4">16px gap between items</div>
```

### Width/Height
```html
<div class="w-full">100% width</div>
<div class="w-auto">Auto width</div>
<div class="w-50">50% width</div>

<div class="h-full">100% height</div>
<div class="h-screen">100vh height</div>

<div class="max-w-lg">Max width 32rem</div>
<div class="max-w-full">Max width 100%</div>
```

### Borders & Shadows
```html
<!-- Borders -->
<div class="border">All sides border</div>
<div class="border-t">Top border</div>
<div class="border-b">Bottom border</div>

<!-- Border radius -->
<div class="rounded">4px border radius</div>
<div class="rounded-md">6px border radius</div>
<div class="rounded-lg">8px border radius</div>
<div class="rounded-full">Fully rounded</div>

<!-- Shadows -->
<div class="shadow-sm">Small shadow</div>
<div class="shadow">Base shadow</div>
<div class="shadow-md">Medium shadow</div>
<div class="shadow-lg">Large shadow</div>
```

### Backgrounds
```html
<div class="bg-primary">Primary background</div>
<div class="bg-secondary">Secondary background</div>
<div class="bg-tertiary">Tertiary background</div>
<div class="bg-accent">Accent background</div>
```

### Position
```html
<div class="position-relative">Relative</div>
<div class="position-absolute">Absolute</div>
<div class="position-fixed">Fixed</div>
<div class="position-sticky">Sticky</div>
```

### Misc
```html
<!-- Overflow -->
<div class="overflow-auto">Auto overflow</div>
<div class="overflow-hidden">Hidden overflow</div>

<!-- Cursor -->
<div class="cursor-pointer">Pointer cursor</div>
<div class="cursor-not-allowed">Not allowed cursor</div>

<!-- User Select -->
<div class="select-none">Not selectable</div>
<div class="select-all">Select all on click</div>

<!-- Opacity -->
<div class="opacity-0">Invisible</div>
<div class="opacity-50">50% opacity</div>
<div class="opacity-100">Fully visible</div>
```

## Common Patterns

### Centered Content
```html
<!-- Horizontally centered -->
<div class="mx-auto max-w-lg">
  Centered content with max width
</div>

<!-- Fully centered -->
<div class="d-flex justify-center items-center h-screen">
  Centered vertically and horizontally
</div>
```

### Card Grid
```html
<div class="grid grid-cols-3 gap-6">
  <div class="card">Card 1</div>
  <div class="card">Card 2</div>
  <div class="card">Card 3</div>
</div>
```

### Section Spacing
```html
<section class="py-12">
  <div class="container">
    <h2 class="mb-6">Section Title</h2>
    <p class="mb-4">Content</p>
  </div>
</section>
```

### Feature List
```html
<div class="grid grid-cols-2 gap-6 my-8">
  <div class="card card-feature">
    <div class="card-icon">🔒</div>
    <h3 class="card-title">Secure</h3>
    <p>Built with security first</p>
  </div>
  <div class="card card-feature">
    <div class="card-icon">⚡</div>
    <h3 class="card-title">Fast</h3>
    <p>Lightning fast performance</p>
  </div>
</div>
```

## Dark Mode

Dark mode is automatic via `prefers-color-scheme`. All CSS custom properties automatically switch.

To manually override:
```html
<html data-theme="dark">  <!-- Force dark mode -->
<html data-theme="light"> <!-- Force light mode -->
```

## Accessibility

Always include:
- Semantic HTML
- ARIA labels where needed
- Focus states (automatically styled)
- Alt text for images
- Proper heading hierarchy

```html
<!-- Good -->
<button class="btn btn-primary" aria-label="Close dialog">
  <span aria-hidden="true">×</span>
</button>

<img src="logo.png" alt="AgentWeave Logo">

<!-- Screen reader only text -->
<span class="sr-only">Additional context for screen readers</span>
```

## Print Styles

Print-specific styles are included. To hide elements when printing:
```html
<div class="no-print">Won't appear in print</div>
```

## Responsive Breakpoints

```scss
// Mobile first approach
.element {
  // Mobile styles (default)
  padding: 1rem;

  // Tablet (768px+)
  @media (min-width: $breakpoint-md) {
    padding: 2rem;
  }

  // Desktop (1024px+)
  @media (min-width: $breakpoint-lg) {
    padding: 3rem;
  }
}
```

Use responsive utility classes:
```html
<!-- Hidden on mobile, visible on desktop -->
<div class="d-none d-lg-block">Desktop only</div>

<!-- Visible on mobile, hidden on desktop -->
<div class="d-block d-lg-none">Mobile only</div>
```

---

**Need more examples?** Check the full documentation in `/docs/assets/css/README.md`
