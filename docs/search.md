---
layout: page
title: Search
description: Search the AgentWeave SDK documentation
permalink: /search/
---

<div class="search-container">
  <div class="search-header">
    <h1>Search Documentation</h1>
    <p class="search-subtitle">Find what you need across all AgentWeave SDK documentation</p>
  </div>

  <div class="search-input-wrapper">
    <svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
      <path d="M21 21L16.65 16.65" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <input
      type="text"
      id="search-input"
      class="search-input"
      placeholder="Search documentation... (Press '/' to focus)"
      autocomplete="off"
      aria-label="Search documentation"
    />
    <button id="clear-search" class="clear-button" aria-label="Clear search" style="display: none;">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
  </div>

  <div id="search-stats" class="search-stats" style="display: none;"></div>

  <div id="search-results" class="search-results">
    <div class="search-instructions">
      <h3>Search Tips</h3>
      <ul>
        <li><strong>Press <kbd>/</kbd></strong> from anywhere to focus the search box</li>
        <li><strong>Press <kbd>Esc</kbd></strong> to clear your search</li>
        <li>Search across all documentation pages, tutorials, guides, and API references</li>
        <li>Results update as you type with matching content highlighted</li>
        <li>Use specific terms for better results (e.g., "SPIFFE identity" instead of just "identity")</li>
      </ul>

      <h3>Popular Topics</h3>
      <div class="popular-topics">
        <a href="{{ '/getting-started/quickstart/' | relative_url }}" class="topic-link">Quick Start</a>
        <a href="{{ '/core-concepts/identity/' | relative_url }}" class="topic-link">Agent Identity</a>
        <a href="{{ '/core-concepts/authorization/' | relative_url }}" class="topic-link">Authorization</a>
        <a href="{{ '/core-concepts/communication/' | relative_url }}" class="topic-link">A2A Protocol</a>
        <a href="{{ '/tutorials/first-agent/' | relative_url }}" class="topic-link">First Agent Tutorial</a>
        <a href="{{ '/api-reference/agent/' | relative_url }}" class="topic-link">Agent API</a>
        <a href="{{ '/deployment/kubernetes/' | relative_url }}" class="topic-link">Kubernetes Deployment</a>
        <a href="{{ '/security/best-practices/' | relative_url }}" class="topic-link">Security Best Practices</a>
      </div>

      <h3>Browse by Category</h3>
      <div class="category-grid">
        <a href="{{ '/getting-started/' | relative_url }}" class="category-card">
          <h4>Getting Started</h4>
          <p>Installation, configuration, and quick start guides</p>
        </a>
        <a href="{{ '/core-concepts/' | relative_url }}" class="category-card">
          <h4>Core Concepts</h4>
          <p>Identity, authorization, protocols, and architecture</p>
        </a>
        <a href="{{ '/tutorials/' | relative_url }}" class="category-card">
          <h4>Tutorials</h4>
          <p>Step-by-step guides for common tasks</p>
        </a>
        <a href="{{ '/guides/' | relative_url }}" class="category-card">
          <h4>How-To Guides</h4>
          <p>Practical solutions for specific problems</p>
        </a>
        <a href="{{ '/api-reference/' | relative_url }}" class="category-card">
          <h4>API Reference</h4>
          <p>Complete API documentation and signatures</p>
        </a>
        <a href="{{ '/examples/' | relative_url }}" class="category-card">
          <h4>Examples</h4>
          <p>Real-world code examples and patterns</p>
        </a>
        <a href="{{ '/deployment/' | relative_url }}" class="category-card">
          <h4>Deployment</h4>
          <p>Deploy to Docker, Kubernetes, and cloud platforms</p>
        </a>
        <a href="{{ '/security/' | relative_url }}" class="category-card">
          <h4>Security</h4>
          <p>Security model, best practices, and compliance</p>
        </a>
      </div>
    </div>
  </div>

  <div id="search-loading" class="search-loading" style="display: none;">
    <div class="spinner"></div>
    <p>Initializing search index...</p>
  </div>
</div>

<script src="https://unpkg.com/lunr@2.3.9/lunr.min.js"></script>
<script src="{{ '/assets/js/search.js' | relative_url }}"></script>

<style>
.search-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.search-header {
  text-align: center;
  margin-bottom: 2rem;
}

.search-header h1 {
  margin-bottom: 0.5rem;
}

.search-subtitle {
  color: var(--color-text-secondary, #666);
  font-size: 1.1rem;
}

.search-input-wrapper {
  position: relative;
  margin-bottom: 1.5rem;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-secondary, #666);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 1rem 3rem 1rem 3.5rem;
  font-size: 1.1rem;
  border: 2px solid var(--color-border, #ddd);
  border-radius: 0.5rem;
  background: var(--color-bg, #fff);
  transition: all 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary, #0066cc);
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.clear-button {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  color: var(--color-text-secondary, #666);
  border-radius: 0.25rem;
  transition: all 0.2s ease;
}

.clear-button:hover {
  background: var(--color-bg-secondary, #f5f5f5);
  color: var(--color-text, #333);
}

.search-stats {
  margin-bottom: 1rem;
  color: var(--color-text-secondary, #666);
  font-size: 0.9rem;
}

.search-results {
  margin-top: 2rem;
}

.search-result {
  padding: 1.5rem;
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  background: var(--color-bg, #fff);
  transition: all 0.2s ease;
}

.search-result:hover {
  border-color: var(--color-primary, #0066cc);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.search-result-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.3rem;
}

.search-result-title a {
  color: var(--color-primary, #0066cc);
  text-decoration: none;
}

.search-result-title a:hover {
  text-decoration: underline;
}

.search-result-path {
  font-size: 0.85rem;
  color: var(--color-text-secondary, #666);
  margin-bottom: 0.75rem;
}

.search-result-excerpt {
  color: var(--color-text, #333);
  line-height: 1.6;
}

.search-result-excerpt mark {
  background-color: rgba(255, 235, 59, 0.4);
  padding: 0.1rem 0.2rem;
  border-radius: 0.2rem;
  font-weight: 600;
}

.search-instructions {
  background: var(--color-bg-secondary, #f5f5f5);
  border-radius: 0.5rem;
  padding: 2rem;
}

.search-instructions h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-text, #333);
}

.search-instructions ul {
  margin-bottom: 2rem;
}

.search-instructions li {
  margin-bottom: 0.5rem;
}

kbd {
  background: var(--color-bg, #fff);
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.25rem;
  padding: 0.1rem 0.4rem;
  font-family: monospace;
  font-size: 0.9em;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.popular-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 2rem;
}

.topic-link {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: var(--color-bg, #fff);
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.25rem;
  color: var(--color-primary, #0066cc);
  text-decoration: none;
  transition: all 0.2s ease;
}

.topic-link:hover {
  background: var(--color-primary, #0066cc);
  color: white;
  border-color: var(--color-primary, #0066cc);
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.category-card {
  padding: 1.5rem;
  background: var(--color-bg, #fff);
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.5rem;
  text-decoration: none;
  color: var(--color-text, #333);
  transition: all 0.2s ease;
}

.category-card:hover {
  border-color: var(--color-primary, #0066cc);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.category-card h4 {
  margin: 0 0 0.5rem 0;
  color: var(--color-primary, #0066cc);
}

.category-card p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary, #666);
}

.search-loading {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary, #666);
}

.spinner {
  border: 3px solid var(--color-border, #ddd);
  border-top-color: var(--color-primary, #0066cc);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.no-results {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary, #666);
}

.no-results h3 {
  color: var(--color-text, #333);
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .category-grid {
    grid-template-columns: 1fr;
  }

  .popular-topics {
    flex-direction: column;
  }

  .topic-link {
    width: 100%;
    text-align: center;
  }
}
</style>
