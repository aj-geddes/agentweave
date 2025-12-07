# AgentWeave Documentation Search

This directory contains the client-side search functionality for the AgentWeave SDK documentation.

## Overview

The search system uses **Lunr.js**, a client-side full-text search library, to provide fast, offline-capable search across all documentation pages without requiring a backend server.

## Components

### 1. Search Page (`search.md`)
- Main search interface at `/search/`
- Search input with autocomplete
- Results display with highlighting
- Browse by category
- Popular topics
- Keyboard shortcuts (`/` to focus)

### 2. Search JavaScript (`assets/js/search.js`)
- Lunr.js integration
- Index building from JSON data
- Search query processing
- Results rendering with highlighting
- Debounced input for performance
- Keyboard shortcut support

### 3. Search Data Generator (`_plugins/search_data_generator.rb`)
- Jekyll plugin that runs during site build
- Generates `search-data.json` with all searchable content
- Indexes:
  - Page titles
  - Page content (stripped of HTML)
  - Categories and tags
  - Descriptions
- Excludes assets, 404 page, and pages marked with `exclude_from_search: true`

### 4. Main JavaScript (`assets/js/main.js`)
- Enhanced with search keyboard shortcut (`/`)
- Redirects to search page when activated
- Scroll-to-top button functionality

### 5. Navigation Data (`_data/navigation.yml`)
- Complete site navigation structure
- 10 main sections with subsections
- Used for navigation includes and breadcrumbs

### 6. 404 Page (`404.md`)
- Custom error page with helpful links
- Browse documentation sections
- Search integration
- Popular pages
- Report broken link button

### 7. Sitemap (`sitemap.xml`)
- XML sitemap for search engines
- All documentation pages with priorities
- Changefreq hints for crawlers
- Note: `jekyll-sitemap` plugin also generates one automatically

## Features

### Client-Side Search
- No server required (works on GitHub Pages)
- Fast, instant results
- Works offline once page is loaded
- Supports complex queries

### Search Index Fields
The search index includes these fields with different boost values:
- **Title** (boost: 10) - highest priority
- **Content** (boost: 5) - medium priority
- **Category** (boost: 1) - standard priority
- **Tags** (boost: 1) - standard priority

### Keyboard Shortcuts
- **`/`** - Focus search input (from anywhere on site)
- **`Esc`** - Clear search input
- Standard keyboard navigation for results

### Search Features
- Real-time search as you type
- Debounced input (300ms) for performance
- Highlighted matching terms in results
- Smart excerpts showing relevant content
- Result count and statistics
- Maximum 50 results displayed

## Usage

### For Users

1. **Direct Access**: Visit `/search/` page
2. **Keyboard Shortcut**: Press `/` from anywhere
3. **Navigation**: Click search icon in header (if present)

### For Developers

#### Exclude a Page from Search
Add to page front matter:
```yaml
---
title: My Page
exclude_from_search: true
---
```

#### Customize Search Index
Edit `_plugins/search_data_generator.rb` to:
- Change content length limit (default: 5000 chars)
- Add custom fields
- Modify category extraction logic

#### Customize Search UI
Edit `search.md` and `assets/js/search.js`:
- Change debounce delay (default: 300ms)
- Adjust max results (default: 50)
- Modify excerpt length (default: 200 chars)
- Customize styling

#### Customize Search Index Weights
Edit `assets/js/search.js` in the `buildSearchIndex` function:
```javascript
this.field('title', { boost: 10 });     // Highest priority
this.field('content', { boost: 5 });    // Medium priority
this.field('category');                  // Standard priority
this.field('tags');                      // Standard priority
```

## Build Process

1. **Jekyll Build**: When the site builds, `search_data_generator.rb` runs
2. **Data Extraction**: Plugin extracts content from all pages and collections
3. **JSON Generation**: Creates `search-data.json` file
4. **Client Load**: Browser loads JSON and builds Lunr index
5. **Search Ready**: User can search immediately

## Performance Considerations

### Search Index Size
- Content is truncated to 5000 characters per page
- HTML is stripped to reduce size
- Average index size: ~100-500 KB depending on content

### Load Time
- Index builds client-side on first search page load
- Typical build time: 100-500ms
- Cached by browser for subsequent visits

### Optimization Tips
1. **Reduce Index Size**: Lower content truncation limit
2. **Lazy Load**: Only build index when search input is focused
3. **Web Worker**: Move index building to background thread
4. **Prebuilt Index**: Build Lunr index at build time (not runtime)

## Dependencies

- **Lunr.js** (v2.3.9): Client-side search library
- Loaded from CDN: `https://unpkg.com/lunr@2.3.9/lunr.min.js`

### Alternative: Local Hosting
To host Lunr.js locally instead of CDN:

1. Download Lunr.js:
```bash
cd docs/assets/js
curl -O https://unpkg.com/lunr@2.3.9/lunr.min.js
```

2. Update search.md:
```html
<script src="{{ '/assets/js/lunr.min.js' | relative_url }}"></script>
```

## Troubleshooting

### Search Not Working
1. Check browser console for errors
2. Verify `search-data.json` exists at `/agentweave/search-data.json`
3. Check Lunr.js loaded successfully
4. Verify Jekyll plugins are enabled

### Search Data Not Generated
1. Ensure `_plugins/` directory exists
2. Verify Jekyll can run custom plugins (not in safe mode)
3. Check Jekyll build logs for plugin errors
4. GitHub Pages: Custom plugins don't work, use GitHub Actions

### Poor Search Results
1. Increase boost values for title field
2. Adjust content truncation length
3. Add more relevant tags to pages
4. Improve page descriptions

### Slow Search
1. Reduce index size (lower truncation limit)
2. Increase debounce delay
3. Reduce max results shown
4. Implement lazy loading

## GitHub Pages Compatibility

**Important**: GitHub Pages runs Jekyll in safe mode, which disables custom plugins.

### Solutions:

1. **GitHub Actions** (Recommended):
   - Build site with GitHub Actions
   - Deploy to `gh-pages` branch
   - Custom plugins work

2. **Pre-build Locally**:
   - Build site locally
   - Commit `search-data.json` to repo
   - Deploy static files

3. **Alternative Search**:
   - Use Algolia DocSearch (requires approval)
   - Use Google Custom Search
   - Use external search service

## Future Enhancements

Potential improvements:
- [ ] Search suggestions/autocomplete
- [ ] Search history
- [ ] Advanced search filters (by category, date, etc.)
- [ ] Search analytics
- [ ] Fuzzy matching
- [ ] Synonym support
- [ ] Multi-language support
- [ ] Voice search
- [ ] Mobile optimizations
- [ ] Search API for external integration

## Testing

Test search functionality:

1. **Build site**: `bundle exec jekyll build`
2. **Serve locally**: `bundle exec jekyll serve`
3. **Visit**: http://localhost:4000/agentweave/search/
4. **Test queries**: Try various search terms
5. **Check**: Verify results are relevant and complete

## License

Part of the AgentWeave SDK documentation.
