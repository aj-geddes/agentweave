/**
 * AgentWeave Documentation Search
 * Client-side search using Lunr.js
 */

(function() {
  'use strict';

  // Configuration
  const config = {
    searchInputId: 'search-input',
    searchResultsId: 'search-results',
    searchStatsId: 'search-stats',
    searchLoadingId: 'search-loading',
    clearButtonId: 'clear-search',
    debounceDelay: 300,
    maxResults: 50,
    excerptLength: 200
  };

  // State
  let searchIndex = null;
  let searchData = null;
  let debounceTimer = null;

  // Initialize search when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    const searchInput = document.getElementById(config.searchInputId);
    if (!searchInput) return;

    setupKeyboardShortcuts();
    setupSearchInput();
    setupClearButton();
    loadSearchIndex();
  }

  /**
   * Setup keyboard shortcuts
   */
  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
      const searchInput = document.getElementById(config.searchInputId);
      if (!searchInput) return;

      // Press '/' to focus search
      if (e.key === '/' && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }

      // Press 'Escape' to clear search
      if (e.key === 'Escape' && document.activeElement === searchInput) {
        clearSearch();
      }
    });
  }

  /**
   * Setup search input handlers
   */
  function setupSearchInput() {
    const searchInput = document.getElementById(config.searchInputId);
    if (!searchInput) return;

    searchInput.addEventListener('input', function(e) {
      const query = e.target.value.trim();

      // Show/hide clear button
      const clearButton = document.getElementById(config.clearButtonId);
      if (clearButton) {
        clearButton.style.display = query ? 'block' : 'none';
      }

      // Debounce search
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function() {
        performSearch(query);
      }, config.debounceDelay);
    });

    // Check URL parameters for initial search query
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    if (query) {
      searchInput.value = query;
      searchInput.dispatchEvent(new Event('input'));
    }
  }

  /**
   * Setup clear button
   */
  function setupClearButton() {
    const clearButton = document.getElementById(config.clearButtonId);
    if (!clearButton) return;

    clearButton.addEventListener('click', clearSearch);
  }

  /**
   * Clear search input and results
   */
  function clearSearch() {
    const searchInput = document.getElementById(config.searchInputId);
    const clearButton = document.getElementById(config.clearButtonId);

    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }

    if (clearButton) {
      clearButton.style.display = 'none';
    }

    showInstructions();
  }

  /**
   * Load and build search index
   */
  function loadSearchIndex() {
    const loadingEl = document.getElementById(config.searchLoadingId);

    // Show loading indicator
    if (loadingEl) {
      loadingEl.style.display = 'block';
    }

    // Fetch search data
    fetch('/agentweave/search-data.json')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load search data');
        }
        return response.json();
      })
      .then(data => {
        searchData = data;
        buildSearchIndex(data);

        // Hide loading indicator
        if (loadingEl) {
          loadingEl.style.display = 'none';
        }
      })
      .catch(error => {
        console.error('Search initialization error:', error);

        // Show error message
        const resultsEl = document.getElementById(config.searchResultsId);
        if (resultsEl) {
          resultsEl.innerHTML = `
            <div class="search-error">
              <h3>Search Unavailable</h3>
              <p>Unable to load search index. Please try refreshing the page.</p>
            </div>
          `;
        }

        if (loadingEl) {
          loadingEl.style.display = 'none';
        }
      });
  }

  /**
   * Build Lunr search index
   */
  function buildSearchIndex(data) {
    searchIndex = lunr(function() {
      this.ref('id');
      this.field('title', { boost: 10 });
      this.field('content', { boost: 5 });
      this.field('category');
      this.field('tags');

      data.forEach(function(doc, idx) {
        this.add({
          id: idx,
          title: doc.title,
          content: doc.content,
          category: doc.category || '',
          tags: (doc.tags || []).join(' ')
        });
      }, this);
    });

    console.log('Search index built with', data.length, 'documents');
  }

  /**
   * Perform search and display results
   */
  function performSearch(query) {
    if (!query) {
      showInstructions();
      return;
    }

    if (!searchIndex || !searchData) {
      console.warn('Search index not ready');
      return;
    }

    try {
      // Perform search
      const results = searchIndex.search(query);

      // Display results
      displayResults(results, query);

      // Update stats
      updateStats(results.length, query);

    } catch (error) {
      console.error('Search error:', error);
      showError('Invalid search query. Please try different terms.');
    }
  }

  /**
   * Display search results
   */
  function displayResults(results, query) {
    const resultsEl = document.getElementById(config.searchResultsId);
    if (!resultsEl) return;

    if (results.length === 0) {
      resultsEl.innerHTML = `
        <div class="no-results">
          <h3>No results found</h3>
          <p>No pages matched your search for "<strong>${escapeHtml(query)}</strong>"</p>
          <p>Suggestions:</p>
          <ul>
            <li>Check your spelling</li>
            <li>Try different or more general keywords</li>
            <li>Use fewer keywords</li>
            <li>Browse the <a href="/agentweave/">documentation home</a></li>
          </ul>
        </div>
      `;
      return;
    }

    // Limit results
    const limitedResults = results.slice(0, config.maxResults);

    // Build HTML
    const html = limitedResults.map(result => {
      const doc = searchData[result.ref];
      const excerpt = createExcerpt(doc.content, query, config.excerptLength);
      const highlightedTitle = highlightText(doc.title, query);

      return `
        <div class="search-result">
          <h3 class="search-result-title">
            <a href="${doc.url}">${highlightedTitle}</a>
          </h3>
          <div class="search-result-path">${doc.category || 'Documentation'} &raquo; ${doc.title}</div>
          <div class="search-result-excerpt">${excerpt}</div>
        </div>
      `;
    }).join('');

    resultsEl.innerHTML = html;
  }

  /**
   * Update search statistics
   */
  function updateStats(count, query) {
    const statsEl = document.getElementById(config.searchStatsId);
    if (!statsEl) return;

    if (count > 0) {
      const plural = count === 1 ? 'result' : 'results';
      statsEl.innerHTML = `Found <strong>${count}</strong> ${plural} for "<strong>${escapeHtml(query)}</strong>"`;
      statsEl.style.display = 'block';
    } else {
      statsEl.style.display = 'none';
    }
  }

  /**
   * Show instructions (default state)
   */
  function showInstructions() {
    const resultsEl = document.getElementById(config.searchResultsId);
    const statsEl = document.getElementById(config.searchStatsId);

    if (statsEl) {
      statsEl.style.display = 'none';
    }

    if (resultsEl) {
      // Check if instructions already exist
      if (!resultsEl.querySelector('.search-instructions')) {
        // Instructions are part of the initial page HTML
        // Just ensure the stats are hidden
        return;
      }
    }
  }

  /**
   * Show error message
   */
  function showError(message) {
    const resultsEl = document.getElementById(config.searchResultsId);
    if (!resultsEl) return;

    resultsEl.innerHTML = `
      <div class="search-error">
        <h3>Search Error</h3>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }

  /**
   * Create excerpt with highlighted search terms
   */
  function createExcerpt(content, query, maxLength) {
    if (!content) return '';

    // Remove extra whitespace
    content = content.replace(/\s+/g, ' ').trim();

    // Find best matching section
    const queryTerms = query.toLowerCase().split(/\s+/);
    let bestIndex = 0;
    let bestScore = 0;

    for (let i = 0; i < content.length - maxLength; i += Math.floor(maxLength / 4)) {
      const section = content.substr(i, maxLength).toLowerCase();
      const score = queryTerms.reduce((sum, term) => {
        return sum + (section.includes(term) ? 1 : 0);
      }, 0);

      if (score > bestScore) {
        bestScore = score;
        bestIndex = i;
      }
    }

    // Extract excerpt
    let excerpt = content.substr(bestIndex, maxLength);

    // Add ellipsis
    if (bestIndex > 0) {
      excerpt = '...' + excerpt;
    }
    if (bestIndex + maxLength < content.length) {
      excerpt = excerpt + '...';
    }

    // Highlight terms
    excerpt = highlightText(excerpt, query);

    return excerpt;
  }

  /**
   * Highlight search terms in text
   */
  function highlightText(text, query) {
    if (!text || !query) return escapeHtml(text);

    const queryTerms = query.split(/\s+/).filter(term => term.length > 0);
    let highlightedText = escapeHtml(text);

    queryTerms.forEach(term => {
      const regex = new RegExp('(' + escapeRegex(term) + ')', 'gi');
      highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
    });

    return highlightedText;
  }

  /**
   * Escape HTML special characters
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Escape regex special characters
   */
  function escapeRegex(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

})();
