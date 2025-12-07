# Favicon Assets

This directory contains favicon and icon assets for the AgentWeave documentation.

## Current Assets

- `favicon.svg` - Scalable vector favicon (recommended for modern browsers)
- `site.webmanifest` - Web app manifest for progressive web app support

## Missing PNG Assets

The following PNG files are referenced in `_includes/head.html` but need to be generated:

- `favicon-32x32.png` - 32x32 pixel PNG favicon
- `favicon-16x16.png` - 16x16 pixel PNG favicon
- `apple-touch-icon.png` - 180x180 pixel PNG for iOS devices

## Generating PNG Favicons

You can generate PNG favicons from the SVG using one of these methods:

### Method 1: Using ImageMagick (if installed)

```bash
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/docs/assets/favicon

# Generate 16x16 favicon
convert -background none favicon.svg -resize 16x16 favicon-16x16.png

# Generate 32x32 favicon
convert -background none favicon.svg -resize 32x32 favicon-32x32.png

# Generate Apple touch icon
convert -background none favicon.svg -resize 180x180 apple-touch-icon.png
```

### Method 2: Using Node.js sharp library

```bash
npm install sharp svg2png-sharp

node << 'EOF'
const sharp = require('sharp');
const fs = require('fs');

const svgBuffer = fs.readFileSync('favicon.svg');

// Generate 16x16
sharp(svgBuffer)
  .resize(16, 16)
  .png()
  .toFile('favicon-16x16.png');

// Generate 32x32
sharp(svgBuffer)
  .resize(32, 32)
  .png()
  .toFile('favicon-32x32.png');

// Generate Apple touch icon
sharp(svgBuffer)
  .resize(180, 180)
  .png()
  .toFile('apple-touch-icon.png');
EOF
```

### Method 3: Online Converter

1. Upload `favicon.svg` to https://cloudconvert.com/svg-to-png
2. Convert to required sizes (16x16, 32x32, 180x180)
3. Download and save to this directory

### Method 4: Use SVG favicons only (Modern approach)

Update `_includes/head.html` to use SVG favicons only:

```html
<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="alternate icon" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="apple-touch-icon" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="manifest" href="{{ '/assets/favicon/site.webmanifest' | relative_url }}">
```

## Design

The favicon features:
- Shield shape representing security
- Woven mesh pattern representing agent connections
- Lock symbol for cryptographic security
- Gradient from blue (#2563eb) to purple (#7c3aed) matching AgentWeave branding
