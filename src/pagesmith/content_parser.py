"""
Content parsing module for markdown, metadata extraction, and HTML generation.
Handles all markdown-to-HTML conversion, frontmatter parsing, and content extraction.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any

import yaml
import markdown


logger = logging.getLogger(__name__)


class ContentParser:
    """
    Parses and processes markdown content, extracts metadata, and converts to HTML.
    Integrates with shortcodes and plugin system for extended functionality.
    """
    
    # Regex to match ```mermaid fenced code blocks
    _MERMAID_FENCE_RE = re.compile(r'```mermaid\s*\n(.*?)\n[ \t]*```', re.DOTALL)
    
    def __init__(
        self,
        sections_dir: Path,
        default_lang: str,
        shortcode_processor: Any,
        plugin_manager: Any,
    ):
        """
        Initialize ContentParser.
        
        Args:
            sections_dir: Path to sections directory for parent/child detection
            default_lang: Default language code
            shortcode_processor: ShortcodeProcessor instance for processing shortcodes
            plugin_manager: PluginManager instance for markdown extensions
        """
        self.sections_dir = sections_dir
        self.default_lang = default_lang
        self.shortcode_processor = shortcode_processor
        self.plugin_manager = plugin_manager
        self._shortcode_ctx: Dict[str, Any] = {}
    
    def _convert_mermaid_fenced_blocks(self, text: str) -> str:
        """Convert ```mermaid fenced code blocks to {% mermaid %} shortcode syntax."""
        return self._MERMAID_FENCE_RE.sub(
            lambda m: '{% mermaid %}\n' + m.group(1).strip() + '\n{% endmermaid %}',
            text
        )
    
    def markdown_to_html(
        self,
        markdown_text: str,
        lang: Optional[str] = None,
        current_page: Optional[str] = None,
    ) -> str:
        """
        Convert markdown to HTML with shortcode processing and plugin extensions.
        
        Args:
            markdown_text: The markdown content to convert
            lang: Language code for context
            current_page: Current page identifier for context
            
        Returns:
            HTML string ready for template rendering
        """
        if not markdown_text:
            return ''

        # Determine if current_page is a child page or a parent page
        # A page is a parent if other .md files exist in a subdirectory with the same name
        # E.g., design_patterns/observer is a parent if design_patterns/observer/cpp.md exists
        parent_name: Optional[str] = None
        if current_page and '/' in current_page:
            segments = current_page.split('/')
            # Check if the last segment is a parent page (has a subdirectory with children)
            potential_parent_dir = self.sections_dir / lang / current_page
            has_children = False
            if potential_parent_dir.is_dir() and potential_parent_dir.exists():
                # Check if there are .md files in this directory
                md_files = list(potential_parent_dir.glob('*.md'))
                if md_files:
                    has_children = True
            
            if has_children:
                # This page is itself a parent (e.g., design_patterns/observer with children cpp, function_based, etc.)
                parent_name = current_page
            else:
                # This page is a child; its parent is everything except the last segment
                parent_name = '/'.join(segments[:-1]) if len(segments) > 1 else None
        
        # Calculate page_depth for resolving relative paths to images/
        if current_page is None:
            page_depth = 0
        elif current_page == 'post':
            page_depth = 1
        elif '/' in current_page:
            page_depth = 1 + current_page.count('/')
        else:
            page_depth = 1
        if lang and lang != self.default_lang:
            page_depth += 1

        self._shortcode_ctx.update({
            'lang': lang,
            'current_page': current_page,
            'parent_name': parent_name,
            'page_depth': page_depth,
        })

        # Step 0: Convert ```mermaid fenced blocks to {% mermaid %} shortcodes
        processed = self._convert_mermaid_fenced_blocks(markdown_text)

        # Step 1: Process shortcodes (outputs raw HTML in markdown)
        processed = self.shortcode_processor.process(processed)

        # Clear context after shortcode processing
        self._shortcode_ctx.clear()

        # Step 2: Get extensions (base + plugin-provided)
        extensions = ['extra', 'tables', 'codehilite', 'fenced_code']
        plugin_extensions = self.plugin_manager.get_markdown_extensions()
        for ext in plugin_extensions:
            if ext not in extensions:
                extensions.append(ext)

        # Step 3: Convert to HTML
        html_output = markdown.markdown(processed, extensions=extensions, extension_configs={
            'codehilite': {
                'css_class': 'codehilite',
                'guess_lang': False
            }
        })

        # Step 4: Run after_content_parse hooks as a filter chain so multiple
        # plugins compose their transformations instead of overwriting.
        html_output = self.plugin_manager.run_filter_hooks(
            'after_content_parse', html_output, markdown_text
        )

        return html_output
    
    def _markdown_inline(self, text: str) -> str:
        """Convert inline markdown to HTML without block-level wrappers."""
        if not text:
            return ''
        html = markdown.markdown(text, extensions=['extra'])
        html = re.sub(r'^<p>(.*)</p>\n?$', r'\1', html, flags=re.DOTALL)
        return html.strip()
    
    def extract_hero_parts(self, markdown_text: str) -> Dict[str, str]:
        """
        Extract title and subtitle from hero markdown.

        The first non-empty line is the title (a leading Markdown heading
        marker like ``# `` is stripped); the second is the subtitle.

        Args:
            markdown_text: The hero markdown content
            
        Returns:
            Dict with 'title' and 'subtitle' keys
        """
        lines = markdown_text.strip().split('\n')
        title = ""
        subtitle = ""
        
        for line in lines:
            line = line.strip()
            if line and not title:
                if line.startswith('#'):
                    line = re.sub(r'^#+\s*', '', line).strip()
                title = line
            elif line and title and not subtitle:
                subtitle = line
                break
        
        return {'title': title, 'subtitle': subtitle}
    
    def extract_cards(self, markdown_text: str) -> List[Dict[str, str]]:
        """
        Extract cards from markdown list format: - **Title**: Description
        
        Args:
            markdown_text: Markdown content with card list
            
        Returns:
            List of dicts with 'title' and 'description' keys
        """
        cards = []
        lines = markdown_text.strip().split('\n')
        
        for line in lines:
            if line.strip().startswith('- **'):
                match = re.match(r'- \*\*(.*?)\*\*:\s*(.*)', line.strip())
                if match:
                    cards.append({
                        'title': match.group(1),
                        'description': match.group(2)
                    })
        
        return cards
    
    def parse_metadata(self, text: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse metadata from document.
        Looks for YAML-style separator (---) at the start of the document.
        
        Args:
            text: The full document text (metadata + content)
            
        Returns:
            Tuple of (metadata_dict, content_text)
        """
        lines = text.strip().split('\n')
        
        # Frontmatter must open with an exact '---' line (not a bullet list item
        # like '- foo' nor a longer rule like '----').
        if not lines or lines[0].strip() != '---':
            return {}, text
        
        # Find the closing '---' separator (exact match), starting after line 0.
        separator_end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                separator_end_idx = i
                break
        
        # No closing separator found
        if separator_end_idx == -1:
            return {}, text
        
        # Extract metadata section (between separators)
        metadata_text = '\n'.join(lines[1:separator_end_idx])
        content_text = '\n'.join(lines[separator_end_idx + 1:])
        
        # Parse YAML metadata
        metadata: Dict[str, Any] = {}
        try:
            metadata = yaml.safe_load(metadata_text) or {}
        except yaml.YAMLError as e:
            logger.warning("Invalid YAML metadata: %s", e)
        
        return metadata, content_text.strip()
    
    def extract_title_from_markdown(
        self,
        markdown_text: str,
        metadata: Dict[str, Any],
        fallback: str = '',
    ) -> Tuple[str, str]:
        """
        Extract a page title from markdown, metadata, or a fallback, in that order.
        
        If the first content line is a top-level heading (`# Title`), it is used
        as the title and removed from the returned content. Otherwise the title
        comes from metadata['title'] (or the provided fallback) and the content
        is returned unchanged.
        
        Args:
            markdown_text: Markdown content with any frontmatter already stripped
            metadata: Parsed frontmatter metadata dict
            fallback: Fallback title if not present in markdown or metadata
            
        Returns:
            Tuple of (title, content_without_title_line)
        """
        lines = markdown_text.strip().split('\n')
        
        if lines and lines[0].startswith('# '):
            title = lines[0].lstrip('# ').strip()
            content = '\n'.join(lines[1:])
            return title, content
        
        title = metadata.get('title', fallback)
        return title, markdown_text
    
    def extract_excerpt(self, markdown_text: str, html_content: str) -> str:
        """
        Extract excerpt from post content.
        First checks for <!--more--> tag in markdown, then falls back to first <p> tag in HTML.
        
        Args:
            markdown_text: The markdown content (before HTML conversion)
            html_content: The HTML content (for fallback extraction)
            
        Returns:
            The excerpt HTML or empty string
        """
        # Check for <!--more--> tag in markdown
        if markdown_text and '<!--more-->' in markdown_text:
            excerpt_markdown = markdown_text.split('<!--more-->')[0].strip()
            if excerpt_markdown:
                return self.markdown_to_html(excerpt_markdown)
        
        # Fall back to first <p> tag from HTML
        if html_content:
            match = re.search(r'<p>(.*?)</p>', html_content)
            if match:
                return f'<p>{match.group(1)}</p>'
        
        return ''
    
    def extract_about_parts(self, markdown_text: str) -> Dict[str, Any]:
        """
        Extract about content and expertise list from markdown.
        
        Args:
            markdown_text: The about page markdown content
            
        Returns:
            Dict with 'content' (HTML) and 'expertise' (list of items) keys
        """
        lines = markdown_text.strip().split('\n')
        
        content_lines = []
        expertise_items = []
        in_list = False
        
        for i, line in enumerate(lines[1:], 1):  # Skip title line
            if line.strip().startswith('## '):
                continue
            elif line.strip().startswith('- '):
                in_list = True
                expertise_items.append(line.strip()[2:])
            elif in_list and line.strip() and not line.strip().startswith('- '):
                in_list = False
                if not line.startswith('#'):
                    content_lines.append(line)
            elif not in_list and line.strip() and not line.startswith('#'):
                content_lines.append(line)
        
        # Build content HTML
        content_html = ""
        for line in content_lines:
            if line.strip():
                content_html += f"<p>{line.strip()}</p>\n"
        
        return {
            'content': content_html.strip(),
            'expertise': expertise_items
        }
    
    def set_shortcode_context(self, context: Dict[str, Any]) -> None:
        """
        Set the context for shortcode processing.
        Called before markdown_to_html when shortcodes need page context.
        Binds the given dict directly so that updates made here (e.g. the
        recomputed parent_name) are visible to shortcode handlers that hold a
        reference to the builder's shared context dict.
        """
        self._shortcode_ctx = context
    
    def get_shortcode_context(self) -> Dict[str, Any]:
        """Get the current shortcode context."""
        return self._shortcode_ctx
