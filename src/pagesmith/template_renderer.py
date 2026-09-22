"""
Template rendering component for Jinja2 template management.
Centralizes template retrieval, context building, and HTML output.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import logging


logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Encapsulates Jinja2 template rendering with context building and file output.
    
    Provides unified interface for:
    - Building standard context dicts (translations, data, URLs, etc.)
    - Rendering templates with given context
    - Writing HTML files with language-aware paths
    - Combined render-and-write operations
    
    Accesses SiteBuilder dependencies via site_builder reference.
    """
    
    def __init__(self, site_builder):
        """Initialize TemplateRenderer with SiteBuilder instance.
        
        Args:
            site_builder: SiteBuilder instance providing access to:
                - env: Jinja2 Environment
                - config: Site configuration dict
                - translation_manager: TranslationManager
                - output_dir: Output directory Path
                - default_lang: Default language code
                - languages: Languages dict
                - build_year: Build year
                - Methods: load_data(), get_urls(), get_language_urls()
        """
        self.site_builder = site_builder
        self.env = site_builder.env
        self.config = site_builder.config
        self.output_dir = site_builder.output_dir
        self.default_lang = site_builder.default_lang
    
    def get_standard_context(self, page_id: str, lang: str, page_type: str = 'section',
                            taxonomy_slug: Optional[str] = None) -> Dict[str, Any]:
        """Build standard context dict for template rendering.
        
        Returns dict with these standard keys (always present):
        - t: Translations for current language
        - data: YAML data files
        - urls: Navigation URLs (relative)
        - languages: Language switcher data
        - lang: Language info dict with 'code' key
        - site: Site configuration
        - current_page: Page identifier (for nav active state)
        - year: Build year
        
        Args:
            page_id: Page identifier (e.g., 'index', 'about', 'post', 'blog')
            lang: Language code (e.g., 'en', 'pl')
            page_type: Page type for language URL generation ('section', 'post', 'blog', 'taxonomy')
            taxonomy_slug: Optional slug for taxonomy pages
        
        Returns:
            Dict with standard context variables
        """
        return {
            't': self.site_builder.translation_manager.load(lang),
            'data': self.site_builder.load_data(),
            'urls': self.site_builder.get_urls(page_id, lang, page_type),
            'languages': self.site_builder.get_language_urls(page_id, lang, page_type, taxonomy_slug),
            'lang': self.site_builder.languages[lang] | {'code': lang},
            'site': self.config['site'],
            'current_page': page_id,
            'year': self.site_builder.build_year,
        }
    
    def render(self, template_name: str, context_dict: Dict[str, Any]) -> str:
        """Render template with given context dict.
        
        Args:
            template_name: Template filename (e.g., 'index.html', 'post.html')
            context_dict: Context dict with all template variables
        
        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(**context_dict)
    
    def write_output(self, html: str, path_segments: str, lang: str) -> Path:
        """Write HTML to language-aware output path using an atomic write.

        For default language, writes to: output_dir/{path_segments}
        For other languages, writes to: output_dir/{lang}/{path_segments}

        The content is first written to a temporary file in the same
        directory and then atomically renamed to its final location, so an
        interruption mid-write never leaves a truncated/corrupted page.

        Creates parent directories as needed.
        Logs generated file path.

        Args:
            html: HTML content to write
            path_segments: Relative path from output_dir (e.g., 'index.html', 'posts/my-post.html')
            lang: Language code

        Returns:
            Path object of written file
        """
        # Determine language-aware output path
        if lang == self.default_lang:
            output_path = self.output_dir / path_segments
        else:
            output_path = self.output_dir / lang / path_segments
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to a temp file in the same directory (same filesystem),
        # then atomically rename into place.
        temp_fd, temp_path = tempfile.mkstemp(
            dir=output_path.parent, prefix='.tmp_', suffix='.html'
        )
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(html)
            os.replace(temp_path, output_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
        
        # Log generated file
        logger.debug("Generated %s", output_path)
        
        return output_path
    
    def render_and_write(self, template_name: str, context_dict: Dict[str, Any],
                        path_segments: str, lang: str) -> Path:
        """Render template and write HTML file in one call.
        
        Convenience method combining render() and write_output().
        
        Args:
            template_name: Template filename
            context_dict: Context dict with all template variables
            path_segments: Relative path from output_dir
            lang: Language code
        
        Returns:
            Path object of written file
        """
        html = self.render(template_name, context_dict)
        return self.write_output(html, path_segments, lang)
