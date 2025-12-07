#!/bin/bash
# Generate PNG favicons from SVG source

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Generating PNG favicons from favicon.svg..."

# Check if ImageMagick is installed
if command -v convert &> /dev/null; then
    echo "Using ImageMagick (convert)..."

    convert -background none favicon.svg -resize 16x16 favicon-16x16.png
    echo "✓ Generated favicon-16x16.png"

    convert -background none favicon.svg -resize 32x32 favicon-32x32.png
    echo "✓ Generated favicon-32x32.png"

    convert -background none favicon.svg -resize 180x180 apple-touch-icon.png
    echo "✓ Generated apple-touch-icon.png"

    echo "All PNG favicons generated successfully!"
    exit 0
fi

# Check if rsvg-convert is installed (librsvg)
if command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert..."

    rsvg-convert -w 16 -h 16 favicon.svg -o favicon-16x16.png
    echo "✓ Generated favicon-16x16.png"

    rsvg-convert -w 32 -h 32 favicon.svg -o favicon-32x32.png
    echo "✓ Generated favicon-32x32.png"

    rsvg-convert -w 180 -h 180 favicon.svg -o apple-touch-icon.png
    echo "✓ Generated apple-touch-icon.png"

    echo "All PNG favicons generated successfully!"
    exit 0
fi

# Check if Inkscape is installed
if command -v inkscape &> /dev/null; then
    echo "Using Inkscape..."

    inkscape favicon.svg --export-filename=favicon-16x16.png --export-width=16 --export-height=16
    echo "✓ Generated favicon-16x16.png"

    inkscape favicon.svg --export-filename=favicon-32x32.png --export-width=32 --export-height=32
    echo "✓ Generated favicon-32x32.png"

    inkscape favicon.svg --export-filename=apple-touch-icon.png --export-width=180 --export-height=180
    echo "✓ Generated apple-touch-icon.png"

    echo "All PNG favicons generated successfully!"
    exit 0
fi

echo "ERROR: No suitable SVG to PNG converter found!"
echo ""
echo "Please install one of the following:"
echo "  - ImageMagick: sudo apt-get install imagemagick"
echo "  - librsvg: sudo apt-get install librsvg2-bin"
echo "  - Inkscape: sudo apt-get install inkscape"
echo ""
echo "Or use an online converter and manually create the PNG files."
echo "See README.md for more options."
exit 1
