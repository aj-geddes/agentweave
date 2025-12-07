# AgentWeave Documentation Assets

This directory contains all assets for the AgentWeave SDK documentation site.

## Quick Links

- **[Completion Summary](COMPLETION_SUMMARY.md)** - Full project completion report
- **[Asset Inventory](ASSETS_CREATED.md)** - Detailed list of all created assets
- **[Verification](VERIFICATION.md)** - Testing and verification checklist
- **[Logo Design](images/LOGO_DESIGN.md)** - Logo design philosophy and guidelines
- **[Favicon Instructions](favicon/INSTALL_INSTRUCTIONS.md)** - How to upgrade favicons

## Directory Structure

```
assets/
├── README.md                   ← You are here
├── ASSETS_CREATED.md          ← Asset inventory
├── COMPLETION_SUMMARY.md      ← Project summary
├── VERIFICATION.md            ← Verification checklist
│
├── css/                       ← Stylesheets
│   ├── home.css
│   ├── main.css
│   ├── main.scss
│   └── syntax.css
│
├── favicon/                   ← Favicon assets
│   ├── README.md             ← Favicon documentation
│   ├── INSTALL_INSTRUCTIONS.md ← Setup guide
│   ├── generate-pngs.sh      ← PNG generation script
│   ├── favicon.svg           ← SVG favicon (primary)
│   ├── favicon-16x16.png     ← 16px PNG fallback
│   ├── favicon-32x32.png     ← 32px PNG fallback
│   ├── apple-touch-icon.png  ← iOS home screen icon
│   └── site.webmanifest      ← PWA manifest
│
├── images/                    ← Logo and images
│   ├── LOGO_DESIGN.md        ← Logo documentation
│   └── logo.svg              ← AgentWeave logo
│
└── js/                        ← JavaScript
    ├── main.js
    └── search.js
```

## Asset Files

### Logos

| File | Description | Size | Format |
|------|-------------|------|--------|
| `images/logo.svg` | Main AgentWeave logo | 3.2 KB | SVG |

**Design**: Shield with woven mesh pattern, blue-to-purple gradient, animated pulse

### Favicons

| File | Description | Size | Format |
|------|-------------|------|--------|
| `favicon/favicon.svg` | Primary favicon | 1.2 KB | SVG |
| `favicon/favicon-16x16.png` | 16×16 fallback | 79 B | PNG |
| `favicon/favicon-32x32.png` | 32×32 fallback | 99 B | PNG |
| `favicon/apple-touch-icon.png` | iOS icon (180×180) | 495 B | PNG |
| `favicon/site.webmanifest` | PWA manifest | 526 B | JSON |

**Note**: PNG files are currently solid-color placeholders. Modern browsers will use the SVG favicon.

### Stylesheets

| File | Description | Type |
|------|-------------|------|
| `css/main.css` | Compiled main stylesheet | CSS |
| `css/main.scss` | Main SASS source | SCSS |
| `css/home.css` | Homepage styles | CSS |
| `css/syntax.css` | Code syntax highlighting | CSS |

### JavaScript

| File | Description | Purpose |
|------|-------------|---------|
| `js/main.js` | Main JavaScript | Navigation, UI |
| `js/search.js` | Search functionality | Site search |

## Status

✅ All required assets created
✅ All 404 errors resolved
✅ Documentation complete
✅ Production ready

## Resolved 404 Errors

The following 404 errors have been fixed:

1. ✅ `/assets/images/logo.svg`
2. ✅ `/assets/favicon/favicon-32x32.png`
3. ✅ `/assets/favicon/favicon-16x16.png`
4. ✅ `/assets/favicon/site.webmanifest`

## Upgrading PNG Favicons

The current PNG favicons are functional placeholders. To upgrade them to match the SVG design:

### Quick Option: Run the script
```bash
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/docs/assets/favicon
./generate-pngs.sh
```

This requires ImageMagick, librsvg, or Inkscape to be installed.

### Alternative: Use online tool
1. Visit https://realfavicongenerator.net/
2. Upload `favicon/favicon.svg`
3. Download generated PNGs
4. Replace existing PNG files

See [favicon/INSTALL_INSTRUCTIONS.md](favicon/INSTALL_INSTRUCTIONS.md) for detailed instructions.

## Color Palette

| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Primary Blue | `#2563eb` | 37, 99, 235 | Main brand color |
| Secondary Purple | `#7c3aed` | 124, 58, 237 | Accent color |
| White | `#ffffff` | 255, 255, 255 | Background, icons |
| Dark | `#1a202c` | 26, 32, 44 | Dark mode background |

## Browser Compatibility

- **SVG Favicons**: Chrome 80+, Firefox 41+, Safari 12+, Edge 79+
- **PNG Fallbacks**: All browsers including legacy versions
- **Web Manifest**: Modern browsers with PWA support

## Usage in Templates

Favicons are referenced in `_includes/head.html`:

```html
<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="icon" type="image/png" sizes="32x32" href="{{ '/assets/favicon/favicon-32x32.png' | relative_url }}">
<link rel="icon" type="image/png" sizes="16x16" href="{{ '/assets/favicon/favicon-16x16.png' | relative_url }}">
<link rel="apple-touch-icon" sizes="180x180" href="{{ '/assets/favicon/apple-touch-icon.png' | relative_url }}">
<link rel="manifest" href="{{ '/assets/favicon/site.webmanifest' | relative_url }}">
```

Logo is used in JSON-LD structured data:

```html
"logo": {
  "@type": "ImageObject",
  "url": "{{ site.url }}/assets/images/logo.svg"
}
```

## Contributing

When adding new assets:

1. Place them in the appropriate subdirectory
2. Update this README.md
3. Follow the established naming conventions
4. Optimize file sizes (especially images)
5. Update relevant documentation

## License

Assets created for the AgentWeave SDK Documentation project.

Logo and branding assets are part of the AgentWeave SDK project.

---

**Last Updated**: December 7, 2025
**Status**: Production Ready
**Created by**: Claude Code
