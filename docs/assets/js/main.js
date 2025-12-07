/* AgentWeave SDK Documentation - Main JavaScript */

(function() {
  'use strict';

  // Theme Management
  const themeManager = {
    init: function() {
      const themeToggle = document.querySelector('.theme-toggle');
      if (themeToggle) {
        themeToggle.addEventListener('click', this.toggleTheme.bind(this));
      }

      // Listen for system theme changes
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          this.setTheme(e.matches ? 'dark' : 'light');
        }
      });
    },

    toggleTheme: function() {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      this.setTheme(newTheme);
    },

    setTheme: function(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);

      // Update theme toggle button aria-label
      const themeToggle = document.querySelector('.theme-toggle');
      if (themeToggle) {
        themeToggle.setAttribute('aria-label',
          theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
        );
      }
    }
  };

  // Mobile Menu
  const mobileMenu = {
    init: function() {
      const menuToggle = document.querySelector('.mobile-menu-toggle');
      const mainNav = document.querySelector('.main-navigation');

      if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
          const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
          menuToggle.setAttribute('aria-expanded', !isExpanded);
          mainNav.classList.toggle('mobile-open');
        });
      }
    }
  };

  // Search Functionality
  const search = {
    init: function() {
      const searchToggle = document.querySelector('.search-toggle');
      if (searchToggle) {
        searchToggle.addEventListener('click', this.openSearch.bind(this));
      }

      // Add keyboard shortcut for search (/)
      document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
          e.preventDefault();
          this.openSearch();
        }
      });
    },

    openSearch: function() {
      // Redirect to search page
      window.location.href = '/agentweave/search/';
    }
  };

  // Code Block Enhancements
  const codeBlocks = {
    init: function() {
      this.addCopyButtons();
      this.addLanguageLabels();
    },

    addCopyButtons: function() {
      const codeBlocks = document.querySelectorAll('pre code');

      codeBlocks.forEach((block) => {
        const pre = block.parentElement;
        if (pre.querySelector('.code-copy-btn')) return; // Already added

        const button = document.createElement('button');
        button.className = 'code-copy-btn';
        button.textContent = 'Copy';
        button.setAttribute('aria-label', 'Copy code to clipboard');

        button.addEventListener('click', async () => {
          try {
            await navigator.clipboard.writeText(block.textContent);
            button.textContent = 'Copied!';
            button.classList.add('copied');

            setTimeout(() => {
              button.textContent = 'Copy';
              button.classList.remove('copied');
            }, 2000);
          } catch (err) {
            console.error('Failed to copy code:', err);
            button.textContent = 'Error';
          }
        });

        pre.style.position = 'relative';
        pre.appendChild(button);
      });
    },

    addLanguageLabels: function() {
      const codeBlocks = document.querySelectorAll('pre code[class*="language-"]');

      codeBlocks.forEach((block) => {
        const pre = block.parentElement;
        if (pre.querySelector('.code-language-label')) return; // Already added

        const className = block.className;
        const match = className.match(/language-(\w+)/);

        if (match) {
          const language = match[1];
          const label = document.createElement('span');
          label.className = 'code-language-label';
          label.textContent = language;
          pre.appendChild(label);
        }
      });
    }
  };

  // Smooth Scroll for Anchor Links
  const smoothScroll = {
    init: function() {
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          const href = anchor.getAttribute('href');
          if (href === '#') return;

          const target = document.querySelector(href);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });

            // Update URL without jumping
            history.pushState(null, null, href);
          }
        });
      });
    }
  };

  // Active Navigation Highlighting
  const navHighlight = {
    init: function() {
      this.highlightCurrentPage();
      this.highlightOnScroll();
    },

    highlightCurrentPage: function() {
      const currentPath = window.location.pathname;
      const navLinks = document.querySelectorAll('.nav-list a, .header-nav a');

      navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath) {
          link.classList.add('active');
        }
      });
    },

    highlightOnScroll: function() {
      const sections = document.querySelectorAll('[id]');
      const navLinks = document.querySelectorAll('.toc-section a');

      if (sections.length === 0 || navLinks.length === 0) return;

      let debounceTimer;
      window.addEventListener('scroll', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          let current = '';

          sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.pageYOffset >= sectionTop - 100) {
              current = section.getAttribute('id');
            }
          });

          navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
              link.classList.add('active');
            }
          });
        }, 100);
      });
    }
  };

  // External Links
  const externalLinks = {
    init: function() {
      const links = document.querySelectorAll('a[href^="http"]');

      links.forEach(link => {
        const url = new URL(link.href);
        if (url.hostname !== window.location.hostname) {
          link.setAttribute('target', '_blank');
          link.setAttribute('rel', 'noopener noreferrer');

          // Add external link icon
          if (!link.querySelector('.external-icon')) {
            const icon = document.createElement('span');
            icon.className = 'external-icon';
            icon.innerHTML = ' ↗';
            icon.setAttribute('aria-label', '(external link)');
            link.appendChild(icon);
          }
        }
      });
    }
  };

  // Accessibility Enhancements
  const a11y = {
    init: function() {
      // Add skip to content link functionality
      const skipLink = document.querySelector('.skip-to-content');
      if (skipLink) {
        skipLink.addEventListener('click', (e) => {
          e.preventDefault();
          const target = document.querySelector('#main-content, main');
          if (target) {
            target.setAttribute('tabindex', '-1');
            target.focus();
            target.removeAttribute('tabindex');
          }
        });
      }

      // Keyboard navigation for mobile menu
      this.trapFocus();
    },

    trapFocus: function() {
      const mobileMenu = document.querySelector('.main-navigation.mobile-open');
      if (!mobileMenu) return;

      const focusableElements = mobileMenu.querySelectorAll(
        'a[href], button, textarea, input, select'
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      mobileMenu.addEventListener('keydown', (e) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      });
    }
  };

  // Scroll to Top Button
  const scrollToTop = {
    init: function() {
      const button = document.querySelector('.scroll-to-top');
      if (!button) return;

      // Show/hide button based on scroll position
      let ticking = false;
      window.addEventListener('scroll', () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            if (window.scrollY > 400) {
              button.classList.add('visible');
            } else {
              button.classList.remove('visible');
            }
            ticking = false;
          });
          ticking = true;
        }
      });

      // Scroll to top on click
      button.addEventListener('click', () => {
        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
      });
    }
  };

  // Initialize all modules when DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    themeManager.init();
    mobileMenu.init();
    search.init();
    codeBlocks.init();
    smoothScroll.init();
    navHighlight.init();
    externalLinks.init();
    a11y.init();
    scrollToTop.init();
  });

})();
