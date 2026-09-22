"""
PageBuilder: Handles building section pages and child pages.
Extracted from SiteBuilder to separate concerns.
"""

import fnmatch
import html as html_module
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class PageBuilder:
    """Builds section pages and nested child pages for a site."""
    
    def __init__(self, site_builder):
        """
        Initialize PageBuilder with a reference to SiteBuilder.
        
        Args:
            site_builder: The parent SiteBuilder instance
        """
        self.site_builder = site_builder
        
    def discover_child_pages(self, parent_name, lang):
        """
        Discover child pages for a parent page.
        Looks for markdown files in sections/{lang}/{parent_name}/ directory.
        Returns a list of child page metadata sorted by child_order.
        """
        children = []
        parent_dir = self.site_builder.sections_dir / lang / parent_name
        
        if not parent_dir.exists():
            return children
        
        # Find all markdown files in the parent directory
        for md_file in sorted(parent_dir.glob('*.md')):
            child_slug = md_file.stem
            content = self.site_builder.read_file(md_file)
            
            if not content:
                continue
            
            metadata, child_content = self.site_builder.parse_metadata(content)
            
            # Extract title from metadata or markdown (content not needed here)
            child_title, _ = self.site_builder.content_parser.extract_title_from_markdown(
                child_content, metadata, fallback=child_slug
            )
            
            # Relative URL from parent page (same directory level)
            child_url = f'{parent_name}/{child_slug}.html'
            
            children.append({
                'slug': child_slug,
                'title': metadata.get('title', child_title),
                'order': metadata.get('child_order', 999),
                'url': child_url,
            })
        
        # Sort by order
        children.sort(key=lambda x: x['order'])
        return children
    
    def build_section_page(self, page_name, page_config, lang):
        """Build a section page for a specific language."""
        logger.debug("Building %s (%s)", page_name, lang)
        
        # Load markdown
        markdown_text = self.site_builder.load_section_file(page_config['markdown'], lang)
        
        if not markdown_text:
            logger.warning("No content found for %s", page_name)
            return
        
        # Parse metadata and content
        metadata, content_markdown = self.site_builder.parse_metadata(markdown_text)
        
        # Extract title and content
        page_title, content_markdown = self.site_builder.content_parser.extract_title_from_markdown(
            content_markdown, metadata, fallback=page_config.get('title', page_name)
        )
        
        # Collect taxonomy data (tags, categories)
        self.site_builder._register_taxonomy_terms(metadata, lang)
        
        # Run before_render_page hooks
        hook_context = {
            'page_name': page_name,
            'lang': lang,
            'metadata': metadata,
            'content_markdown': content_markdown,
        }
        self.site_builder.plugin_manager.run_hooks('before_render_page', page_name, lang, hook_context)
        
        # Calculate page depth: sections/page_name.html has depth 1
        page_depth = 1
        page_content = self.site_builder.markdown_to_html(content_markdown, lang=lang, current_page=page_name, page_depth=page_depth, parent_name=None)
        
        # Discover child pages
        children = self.discover_child_pages(page_name, lang)
        
        # Merge metadata with page context
        subtitle_raw = metadata.get('subtitle', '')
        subtitle_html = self.site_builder._markdown_inline(subtitle_raw)
        page_context = {
            'title': metadata.get('title', page_title),
            'subtitle': subtitle_html,
            'content': page_content,
            'description': metadata.get('description', ''),
            'keywords': metadata.get('keywords', ''),
            'show_related_pages': metadata.get('show_related_pages', True),
        }
        
        # Build context with standard variables
        context = self.site_builder.template_renderer.get_standard_context(page_name, lang)
        context.update({
            'page': page_context,
            'metadata': metadata,
            'children': children,
        })
        
        # Render template
        html = self.site_builder.template_renderer.render(page_config['template'], context)

        # Run after_render_page hooks
        self.site_builder.plugin_manager.run_hooks('after_render_page', page_name, lang, html)
        
        # Determine output path
        path_segments = f'sections/{page_name}.html'
        
        # Update taxonomy data with page reference and URL
        page_url_from_taxonomy = f'../../sections/{page_name}.html' if lang != self.site_builder.default_lang else f'sections/{page_name}.html'
        self.site_builder._add_taxonomy_post(metadata, lang, {
            'title': metadata.get('title', page_title),
            'subtitle': subtitle_html,
            'slug': page_name,
            'date': metadata.get('date', ''),
            'author': '',  # Pages don't have authors
            'excerpt': '',  # Pages don't have excerpts
            'url': page_url_from_taxonomy,
            'type': 'page',  # Mark as page type
        })
        
        # Write file
        self.site_builder.template_renderer.write_output(html, path_segments, lang)
        
        # Build child pages if any
        if children:
            self.build_child_pages(page_name, lang)
    
    def _read_page_title(self, page_path, lang):
        """Read a page's title from its markdown file given a relative path (without .md)."""
        md_path = (self.site_builder.sections_dir / lang / page_path).with_suffix('.md')
        if not md_path.exists():
            last_part = page_path.split('/')[-1]
            return last_part.replace('_', ' ').title()
        content = self.site_builder.read_file(md_path)
        if not content:
            last_part = page_path.split('/')[-1]
            return last_part.replace('_', ' ').title()
        metadata, content_md = self.site_builder.parse_metadata(content)
        if metadata.get('title'):
            return metadata['title']
        lines = content_md.strip().split('\n')
        if lines and lines[0].startswith('# '):
            return lines[0].lstrip('# ').strip()
        last_part = page_path.split('/')[-1]
        return last_part.replace('_', ' ').title()

    def _get_child_page_title(self, md_file, child_slug):
        """Extract title from a child page's markdown file."""
        content = self.site_builder.read_file(md_file)
        if not content:
            return child_slug
        metadata, content_md = self.site_builder.parse_metadata(content)
        if metadata.get('title'):
            return metadata['title']
        lines = content_md.strip().split('\n')
        if lines and lines[0].startswith('# '):
            return lines[0].lstrip('# ').strip()
        return child_slug

    def _get_child_page_breadcrumbs(self, segments, parent_name, lang, urls, metadata):
        """Build breadcrumbs for a (possibly nested) child page.
        
        segments: list of path segments below the parent, e.g. ['visitor', 'python']
        parent_name: the config-registered parent page name, e.g. 'design_patterns'
        All ancestor titles are automatically read from their markdown files.
        """
        depth = len(segments)
        full_segments = [parent_name] + segments
        
        breadcrumbs = [
            {'title': 'Home', 'url': urls.get('home', './')},
        ]
        
        # Add ancestor pages (all segments except the current page)
        for i in range(depth):
            ancestor_path = '/'.join(full_segments[:i + 1])
            
            # Read parent title from its markdown file
            ancestor_title = self._read_page_title(ancestor_path, lang)
            
            # URL from current page to this ancestor
            levels_up = depth - i
            url = '../' * levels_up + f'{full_segments[i]}.html'
            
            breadcrumbs.append({
                'title': ancestor_title,
                'url': url,
            })
        
        # Current page
        breadcrumbs.append({
            'title': metadata.get('title', segments[-1]),
            'url': None,
        })
        
        return breadcrumbs

    def build_child_pages(self, parent_name, lang, subpath=''):
        """Build all child pages under a parent page, recursively."""
        parent_dir = self.site_builder.sections_dir / lang / parent_name
        child_dir = parent_dir / subpath if subpath else parent_dir
        
        if not child_dir.exists():
            return
        
        for md_file in sorted(child_dir.glob('*.md')):
            child_slug = md_file.stem
            markdown_text = self.site_builder.read_file(md_file)
            
            if not markdown_text:
                continue
            
            # Build the full relative path
            child_path = f'{subpath}/{child_slug}' if subpath else child_slug
            full_child_path = f'{parent_name}/{child_path}'
            
            # Parse metadata and content
            metadata, content_markdown = self.site_builder.parse_metadata(markdown_text)
            
            # Collect taxonomy data (tags, categories)
            self.site_builder._register_taxonomy_terms(metadata, lang)
            
            # Extract title and content
            child_title, content_markdown = self.site_builder.content_parser.extract_title_from_markdown(
                content_markdown, metadata, fallback=child_slug
            )
            
             # Convert to HTML
            # Calculate page depth based on output path: sections/parent/child.html = depth 2
            output_segments = ['sections', parent_name] + child_path.split('/') + ['file']
            page_depth = len(output_segments) - 2  # -1 for 'file', -1 for .html
            page_content = self.site_builder.markdown_to_html(content_markdown, lang=lang, current_page=full_child_path, page_depth=page_depth, parent_name=parent_name)
            
            # Build breadcrumbs
            segments = child_path.split('/')
            urls = self.site_builder.get_urls(full_child_path, lang)
            breadcrumbs = self._get_child_page_breadcrumbs(segments, parent_name, lang, urls, metadata)
            
            # Discover deeper children (grandchildren, etc.)
            child_subpath = f'{subpath}/{child_slug}' if subpath else child_slug
            deeper_children = self.discover_deeper_pages(parent_name, lang, child_subpath)
            
            # Merge metadata with page context
            child_subtitle_raw = metadata.get('subtitle', '')
            child_subtitle_html = self.site_builder._markdown_inline(child_subtitle_raw)
            page_context = {
                'title': metadata.get('title', child_title),
                'subtitle': child_subtitle_html,
                'content': page_content,
                'description': metadata.get('description', ''),
                'keywords': metadata.get('keywords', ''),
                'parent': parent_name,
            }
            
            # Build context with standard variables
            context = self.site_builder.template_renderer.get_standard_context(full_child_path, lang)
            context.update({
                'page': page_context,
                'metadata': metadata,
                'breadcrumbs': breadcrumbs,
                'children': deeper_children,
            })
            
            # Render template
            html = self.site_builder.template_renderer.render('page.html', context)
            
            # Determine output path
            output_segments = ['sections', parent_name]
            if subpath:
                output_segments.extend(subpath.split('/'))
            output_segments.append(f'{child_slug}.html')
            path_segments = '/'.join(output_segments)
            
            # Update taxonomy data with child page reference and URL
            # Build relative URL from taxonomy term page to child page.
            # A term page lives at html/{lang}/tags/{term}/index.html — exactly
            # two levels above the language's sections root in both default and
            # non-default languages (html/tags/{term}/ -> html/; or
            # html/{lang}/tags/{term}/ -> html/{lang}/).
            relative_prefix = '../../'
            page_url_from_taxonomy = f'{relative_prefix}/{"/".join(output_segments)}'
            
            self.site_builder._add_taxonomy_post(metadata, lang, {
                'title': metadata.get('title', child_title),
                'subtitle': child_subtitle_html,
                'slug': full_child_path,
                'date': metadata.get('date', ''),
                'author': '',  # Pages don't have authors
                'excerpt': '',  # Pages don't have excerpts
                'url': page_url_from_taxonomy,
                'type': 'page',  # Mark as page type
            })
            
            # Write file
            self.site_builder.template_renderer.write_output(html, path_segments, lang)
            
            # Recursively build deeper children
            self.build_child_pages(parent_name, lang, child_subpath)

    def discover_deeper_pages(self, parent_name, lang, subpath):
        """Discover child pages under a subpath of a parent page.
        
        E.g., parent_name='design_patterns', subpath='visitor' looks in
        sections/{lang}/design_patterns/visitor/ for *.md files.
        Returns a list sorted by child_order for template rendering.
        
        URLs are relative to the current page (at subpath level).
        """
        child_dir = self.site_builder.sections_dir / lang / parent_name / subpath
        if not child_dir.exists():
            return []
        
        children = []
        for md_file in sorted(child_dir.glob('*.md')):
            child_slug = md_file.stem
            content = self.site_builder.read_file(md_file)
            if not content:
                continue
            metadata, _ = self.site_builder.parse_metadata(content)
            
            child_title = metadata.get('title', child_slug)
            
            # URL relative to the current page (at subpath level)
            # If we're at design_patterns/observer.html, children go in design_patterns/observer/
            # So the URL to a child is just the child_slug with .html extension
            child_url = f'{child_slug}.html'
            
            children.append({
                'slug': child_slug,
                'title': child_title,
                'order': metadata.get('child_order', 999),
                'url': child_url,
            })
        
        children.sort(key=lambda x: x['order'])
        return children
