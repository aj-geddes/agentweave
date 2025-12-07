# Styling System Architecture

## File Dependency Diagram

```
main.scss (Entry Point)
│
├─► _variables.scss          (Design Tokens - No Dependencies)
│   ├─► Color palette (40+ colors)
│   ├─► Typography scale
│   ├─► Spacing system (8px grid)
│   ├─► Breakpoints (6 responsive)
│   ├─► Shadows, borders, transitions
│   └─► CSS Custom Properties (runtime)
│
├─► _base.scss               (Depends on: _variables.scss)
│   ├─► CSS Reset/Normalize
│   ├─► Typography (h1-h6, p, lists)
│   ├─► Links & navigation
│   ├─► Tables
│   ├─► Code blocks (pre, code, kbd)
│   ├─► Forms (basic)
│   ├─► Scrollbar styling
│   ├─► Accessibility helpers
│   └─► Print styles
│
├─► _layout.scss             (Depends on: _variables.scss)
│   ├─► Site wrapper & container
│   ├─► Header (sticky, logo, nav)
│   ├─► Sidebar (collapsible, sticky)
│   ├─► Main content area
│   ├─► Table of Contents (right)
│   ├─► Footer (multi-column)
│   ├─► Grid system (1-4 columns)
│   ├─► Breadcrumbs
│   └─► Content navigation
│
├─► _components.scss         (Depends on: _variables.scss)
│   ├─► Buttons (5 variants)
│   ├─► Code blocks (enhanced)
│   ├─► Callout boxes (6 types)
│   ├─► Cards (3 variants)
│   ├─► Tables (enhanced)
│   ├─► Badges & Tags
│   ├─► Search box
│   ├─► API endpoints
│   ├─► Tabs
│   ├─► Accordion
│   └─► Progress bars
│
└─► _utilities.scss          (Depends on: _variables.scss)
    ├─► Spacing (m-, p-, mx-, my-, etc.)
    ├─► Typography (text-, font-, leading-)
    ├─► Display (d-block, d-flex, d-grid)
    ├─► Flexbox (justify-, items-, gap-)
    ├─► Width/Height (w-full, h-screen)
    ├─► Position (relative, absolute, fixed)
    ├─► Borders & Shadows
    ├─► Backgrounds
    └─► Responsive variants (@media)
```

## Import Order (Critical!)

The order in `main.scss` is important:

```scss
1. _variables.scss    // MUST be first (defines tokens)
2. _base.scss         // Base element styles
3. _layout.scss       // Structural layout
4. _components.scss   // Reusable components
5. _utilities.scss    // MUST be last (highest specificity)
```

## CSS Specificity Layers

```
┌─────────────────────────────────────────┐
│ Layer 5: !important utilities           │  Highest
│ _utilities.scss (with !important)       │  Specificity
├─────────────────────────────────────────┤
│ Layer 4: Component classes              │
│ _components.scss (.btn, .card, etc.)    │
├─────────────────────────────────────────┤
│ Layer 3: Layout classes                 │
│ _layout.scss (.sidebar, .header, etc.)  │
├─────────────────────────────────────────┤
│ Layer 2: Base element styles            │
│ _base.scss (h1, p, a, table, etc.)      │
├─────────────────────────────────────────┤
│ Layer 1: CSS Custom Properties          │  Lowest
│ _variables.scss (:root, [data-theme])   │  Specificity
└─────────────────────────────────────────┘
```

## Design Token Flow

```
Sass Variables (_variables.scss)
        │
        ├─► Compile-time constants
        │   └─► $color-primary-900: #1a365d
        │
        └─► CSS Custom Properties
            └─► --color-primary: #{$color-primary-900}
                        │
                        ├─► Light mode (default)
                        ├─► Dark mode (@media prefers-color-scheme)
                        ├─► Manual dark ([data-theme="dark"])
                        └─► Manual light ([data-theme="light"])
                                    │
                                    └─► Used in components
                                        └─► color: var(--color-primary)
```

## Component Architecture

```
Base Component Structure:
┌────────────────────────────┐
│ .component                 │  Base class
│ ├─► .component-header      │  Subcomponent
│ ├─► .component-body        │  Subcomponent
│ └─► .component-footer      │  Subcomponent
│                            │
│ Modifiers:                 │
│ ├─► .component--variant    │  Variant modifier
│ ├─► .component--size       │  Size modifier
│ └─► .component--state      │  State modifier
└────────────────────────────┘

Example:
.btn                  → Base button
.btn-primary          → Primary variant
.btn-sm               → Small size
.btn-block            → Block modifier
.btn:hover            → Hover state
```

## Responsive Breakpoint System

```
Mobile First Approach:

CSS:                    Screen Size:
─────────────────────────────────────────────────
Base styles        →   All screens (mobile first)
                  ↓
@media (min-width: 640px)  →  sm: tablets
                  ↓
@media (min-width: 768px)  →  md: tablets
                  ↓
@media (min-width: 1024px) →  lg: laptops
                  ↓
@media (min-width: 1280px) →  xl: desktops
                  ↓
@media (min-width: 1536px) →  2xl: large desktops

Utility classes follow same pattern:
.d-none              →  Hidden on all screens
.d-sm-block          →  Block on sm+ screens
.d-md-flex           →  Flex on md+ screens
.d-lg-grid           →  Grid on lg+ screens
```

## Dark Mode Implementation

```
┌─────────────────────────────────────────────┐
│ User Preference Detection                   │
└─────────────────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌──────────┐          ┌──────────────┐
│ System   │          │ Manual       │
│ Pref     │          │ Override     │
└──────────┘          └──────────────┘
      │                       │
      │                       │
      ▼                       ▼
@media                [data-theme="dark"]
(prefers-color-       [data-theme="light"]
 scheme: dark)
      │                       │
      └───────────┬───────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ CSS Variables   │
        │ are updated     │
        └─────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ All components  │
        │ automatically   │
        │ update colors   │
        └─────────────────┘
```

## Color System Architecture

```
Semantic Colors (Light Mode):
┌────────────────────────────────────────┐
│ Color Palette                          │
│ ├─► Primary: #1a365d (Deep Blue)      │
│ ├─► Accent: #0d9488 (Teal)            │
│ ├─► Gray Scale: 50-900                │
│ └─► Semantic: success, warning, etc.  │
└────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│ CSS Custom Properties (Runtime)        │
│ ├─► --color-bg-primary                │
│ ├─► --color-bg-secondary              │
│ ├─► --color-text-primary              │
│ ├─► --color-text-secondary            │
│ ├─► --color-border                    │
│ ├─► --color-link                      │
│ └─► --color-primary                   │
└────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│ Component Usage                        │
│ background-color: var(--color-bg-...)  │
│ color: var(--color-text-...)           │
│ border-color: var(--color-border)      │
└────────────────────────────────────────┘
```

## Spacing System Flow

```
Base Scale (8px grid):
┌─────────────────────┐
│ $spacing-1: 0.25rem │  →  4px
│ $spacing-2: 0.5rem  │  →  8px
│ $spacing-3: 0.75rem │  →  12px
│ $spacing-4: 1rem    │  →  16px
│ $spacing-6: 1.5rem  │  →  24px
│ $spacing-8: 2rem    │  →  32px
│ ...                 │
└─────────────────────┘
        │
        ├─► Used in components
        │   └─► padding: $spacing-4
        │
        └─► Generated utility classes
            ├─► .m-4  { margin: 1rem !important }
            ├─► .p-6  { padding: 1.5rem !important }
            ├─► .mt-8 { margin-top: 2rem !important }
            └─► .px-4 { padding-left/right: 1rem !important }
```

## Typography Scale

```
Type Scale (Major Third - 1.250):
┌────────────────────────────────┐
│ Base: 16px (1rem)              │
├────────────────────────────────┤
│ ÷ 1.250 ↓                      │
│ xs:  12px → .text-xs           │
│ sm:  14px → .text-sm           │
│ base: 16px → .text-base        │
│ × 1.250 ↑                      │
│ md:  18px → .text-md           │
│ lg:  20px → .text-lg           │
│ xl:  24px → .text-xl           │
│ 2xl: 30px → .text-2xl          │
│ 3xl: 36px → .text-3xl          │
│ 4xl: 48px → .text-4xl          │
└────────────────────────────────┘
        │
        ├─► Headings
        │   ├─► h1: $font-size-4xl
        │   ├─► h2: $font-size-3xl
        │   ├─► h3: $font-size-2xl
        │   └─► h4: $font-size-xl
        │
        └─► Utility classes
            └─► .text-lg { font-size: 1.25rem }
```

## Component Composition Example

```
Card Component Breakdown:
┌──────────────────────────────────────┐
│ .card                                │
│ ├─► Base styles (_components.scss)  │
│ │   ├─► background-color             │
│ │   ├─► border                       │
│ │   ├─► border-radius                │
│ │   ├─► padding                      │
│ │   └─► box-shadow                   │
│ │                                    │
│ ├─► .card-header                     │
│ │   ├─► .card-title (h3)             │
│ │   │   └─► Uses _base.scss h3       │
│ │   └─► .card-subtitle               │
│ │                                    │
│ ├─► .card-body                       │
│ │   └─► Content (inherits _base)     │
│ │                                    │
│ └─► .card-footer                     │
│                                      │
│ Variants:                            │
│ ├─► .card-feature (centered)         │
│ └─► .card-link (hoverable)           │
│                                      │
│ Can be enhanced with utilities:      │
│ ├─► .shadow-lg                       │
│ ├─► .rounded-xl                      │
│ └─► .p-6                             │
└──────────────────────────────────────┘
```

## Utility Class Generation Pattern

```
Spacing Utilities Pattern:
┌─────────────────────────────────────┐
│ For each size in spacing scale:    │
│                                     │
│ .m-{size}  { margin: {value} }      │
│ .mt-{size} { margin-top: {value} }  │
│ .mb-{size} { margin-bottom: ... }   │
│ .ml-{size} { margin-left: ... }     │
│ .mr-{size} { margin-right: ... }    │
│ .mx-{size} { margin-left/right: }   │
│ .my-{size} { margin-top/bottom: }   │
│                                     │
│ Same pattern for padding (p-)       │
└─────────────────────────────────────┘

Responsive Utilities Pattern:
┌─────────────────────────────────────┐
│ .d-none    { display: none }        │
│ .d-block   { display: block }       │
│                                     │
│ @media (min-width: $breakpoint-md)  │
│ .d-md-none  { display: none }       │
│ .d-md-block { display: block }      │
│                                     │
│ @media (min-width: $breakpoint-lg)  │
│ .d-lg-none  { display: none }       │
│ .d-lg-block { display: block }      │
└─────────────────────────────────────┘
```

## Build Process

```
Source Files → Sass Compiler → Output
─────────────────────────────────────

_sass/
├─► _variables.scss  ┐
├─► _base.scss       │
├─► _layout.scss     ├─► Sass Processor
├─► _components.scss │   (Jekyll/Node-sass)
└─► _utilities.scss  ┘
         +                     │
assets/css/                    │
└─► main.scss        ──────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │ Process imports  │
                     │ Resolve variables│
                     │ Compile CSS      │
                     └──────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │ Production:      │
                     │ - Minify         │
                     │ - Autoprefixer   │
                     │ - Optimize       │
                     └──────────────────┘
                               │
                               ▼
                        main.css (output)
```

## Best Practice: Cascade Order

```
Least Specific                  Most Specific
─────────────────────────────────────────────
│                                           │
│  Element selectors                        │
│  (h1, p, a)                              │
│  └─► Defined in _base.scss               │
│                                           │
├───────────────────────────────────────────┤
│  Class selectors                          │
│  (.header, .sidebar)                     │
│  └─► Defined in _layout.scss             │
│                                           │
├───────────────────────────────────────────┤
│  Component classes                        │
│  (.btn, .card, .callout)                 │
│  └─► Defined in _components.scss         │
│                                           │
├───────────────────────────────────────────┤
│  Utility classes with !important          │
│  (.mt-4, .d-flex, .text-center)          │
│  └─► Defined in _utilities.scss          │
│                                           │
└───────────────────────────────────────────┘
```

This architecture ensures:
- Predictable specificity
- Easy overrides
- Maintainable code
- Minimal conflicts
