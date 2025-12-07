# Jekyll plugin to generate search data JSON
# This plugin creates a search-data.json file for client-side search

module Jekyll
  class SearchDataGenerator < Generator
    safe true
    priority :low

    def generate(site)
      search_data = []

      # Process all pages
      site.pages.each do |page|
        next if exclude_page?(page)

        search_data << {
          title: page.data['title'] || page.name,
          url: page.url,
          content: strip_html(page.content),
          category: page.data['category'] || get_category_from_url(page.url),
          tags: page.data['tags'] || [],
          description: page.data['description'] || ''
        }
      end

      # Process all collections
      site.collections.each do |label, collection|
        next if ['posts', 'drafts'].include?(label)

        collection.docs.each do |doc|
          search_data << {
            title: doc.data['title'] || doc.basename,
            url: doc.url,
            content: strip_html(doc.content),
            category: doc.data['category'] || label.capitalize,
            tags: doc.data['tags'] || [],
            description: doc.data['description'] || ''
          }
        end
      end

      # Create search data file
      search_file = PageWithoutAFile.new(site, __dir__, '', 'search-data.json')
      search_file.content = JSON.generate(search_data)
      search_file.data['layout'] = nil
      site.pages << search_file
    end

    private

    def exclude_page?(page)
      # Exclude certain pages from search
      excluded_paths = ['/404.html', '/search-data.json']
      excluded_paths.include?(page.url) ||
        page.data['exclude_from_search'] == true ||
        page.url.start_with?('/assets/')
    end

    def strip_html(content)
      return '' if content.nil?

      # Remove HTML tags
      content = content.gsub(/<\/?[^>]*>/, '')

      # Remove extra whitespace
      content = content.gsub(/\s+/, ' ')

      # Remove front matter
      content = content.gsub(/^---.*?---/m, '')

      # Truncate to reasonable length (to keep JSON size manageable)
      content[0..5000].strip
    end

    def get_category_from_url(url)
      parts = url.split('/').reject(&:empty?)
      return 'Documentation' if parts.empty?

      # Convert URL path to category name
      parts.first.split('-').map(&:capitalize).join(' ')
    end
  end
end
