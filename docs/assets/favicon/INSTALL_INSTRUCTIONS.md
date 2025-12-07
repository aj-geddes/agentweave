# Favicon Installation Instructions

## Current Situation

The following SVG assets have been created:
- ✅ `favicon.svg` - Scalable vector favicon
- ✅ `site.webmanifest` - Web app manifest

## Required PNG Files

The following PNG files are referenced in `_includes/head.html` but need to be generated:

1. `favicon-16x16.png` (16×16 pixels)
2. `favicon-32x32.png` (32×32 pixels)
3. `apple-touch-icon.png` (180×180 pixels)

## Quick Fix Options

### Option 1: Use SVG Favicons Only (Recommended - No Installation Required)

Modern browsers support SVG favicons. Update `_includes/head.html` lines 32-35 to:

```html
<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="alternate icon" type="image/svg+xml" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="apple-touch-icon" href="{{ '/assets/favicon/favicon.svg' | relative_url }}">
<link rel="manifest" href="{{ '/assets/favicon/site.webmanifest' | relative_url }}">
```

This will work in all modern browsers (Chrome, Firefox, Safari, Edge) and eliminate the 404 errors.

### Option 2: Generate PNG Files

Run the provided generation script after installing a converter:

```bash
# Install a converter (choose one)
sudo apt-get install imagemagick
# OR
sudo apt-get install librsvg2-bin
# OR
sudo apt-get install inkscape

# Then run the generation script
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/docs/assets/favicon
./generate-pngs.sh
```

### Option 3: Use Online Converter

1. Visit https://realfavicongenerator.net/ or https://favicon.io/
2. Upload `favicon.svg`
3. Download the generated PNG files
4. Place them in this directory

### Option 4: Use Node.js (if available)

```bash
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/docs/assets/favicon

# Install dependencies
npm install sharp

# Generate PNGs
node -e "
const sharp = require('sharp');
const fs = require('fs');
const svg = fs.readFileSync('favicon.svg');

sharp(svg).resize(16, 16).png().toFile('favicon-16x16.png');
sharp(svg).resize(32, 32).png().toFile('favicon-32x32.png');
sharp(svg).resize(180, 180).png().toFile('apple-touch-icon.png');

console.log('PNG files generated!');
"
```

## Browser Support

- **SVG favicons**: Supported by all modern browsers (Chrome 80+, Firefox 41+, Safari 12+, Edge 79+)
- **PNG favicons**: Legacy support for older browsers

## Recommendation

**Use Option 1 (SVG favicons only)** unless you need to support very old browsers. This is the modern, scalable approach and requires no additional tools.
