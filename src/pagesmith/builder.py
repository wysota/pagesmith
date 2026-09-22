"""SiteBuilder: orchestrates building a site from markdown and templates."""

import re
import logging
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .translation_manager import TranslationManager
from .plugins.shortcodes import ShortcodeProcessor
from .plugins.plugin_manager import PluginManager
from .page_builder import PageBuilder
from .content_parser import ContentParser
from .url_manager import URLManager
from .asset_manager import AssetManager
from .taxonomy_manager import TaxonomyManager
from .feed_generator import FeedGenerator
from .template_renderer import TemplateRenderer
from .shortcodes import register_shortcodes
from .paths import (
    builtin_plugins_dir,
    load_site_config,
    package_templates_dir,
    resolve_output_dir,
)


logger = logging.getLogger(__name__)


class SiteBuilder:
    """Static site generator with Jinja2 templating and i18n support."""
    
    def __init__(self, site_dir, output_dir=None, *, templates_dir=None,
                 extra_plugin_dirs=()):
        self.site_dir = Path(site_dir).resolve()
        self.package_dir = Path(__file__).resolve().parent
        self.config = load_site_config(self.site_dir)

        # Directory paths (config paths are relative to site_dir)
        self.content_dir = self.site_dir / self.config['build']['content_dir']
        self.sections_dir = self.site_dir / self.config['build']['sections_dir']
        self.templates_dir = Path(templates_dir) if templates_dir else package_templates_dir()
        self.site_templates_dir = self.site_dir / 'templates'
        self.images_dir = self.site_dir / self.config['build']['images_dir']
        self.output_dir = resolve_output_dir(
            self.site_dir, output=output_dir, config=self.config)
        self.assets_dir = self.site_dir / 'assets'
        self.data_dir = self.site_dir / 'data'
        self.files_dir = self.site_dir / 'files'
        
        # Build timestamp (computed once so a build crossing midnight stays consistent)
        self.build_time = datetime.now()
        self.build_year = self.build_time.year

        # Cache for data
        self.data_cache = None
        self._shortcode_ctx = {}  # Page context for shortcodes: {'lang': str, 'current_page': str}
        
        # Languages config
        self.languages = self.config['languages']
        self.default_lang = self.get_default_language()
        
        # Translation manager
        translations_dir = self.site_dir / 'translations'
        self.translation_manager = TranslationManager(translations_dir, self.default_lang)
        
        # Taxonomy configuration
        self.taxonomies = self.config.get('taxonomies', {
            'tags': {
                'singular': 'tag',
                'plural': 'tags',
                'slug': 'tags',
                'enabled': True,
            },
            'categories': {
                'singular': 'category',
                'plural': 'categories',
                'slug': 'categories',
                'enabled': True,
            },
        })
        
         # Taxonomy data cache: lang -> taxonomy_type -> term_slug -> term_data
        self.taxonomy_data = {}
        
        # Initialize shortcode processor (will register shortcodes later)
        self.shortcode_processor = ShortcodeProcessor()
        
        # Initialize plugin manager, link to shortcode registry, load plugins
        self.plugin_manager = PluginManager(site_builder=self)
        self.plugin_manager.set_shortcode_registry(self.shortcode_processor)
        self.plugin_manager.load_all(builtin_plugins_dir())
        site_plugins = self.site_dir / 'plugins'
        if site_plugins.is_dir():
            self.plugin_manager.load_all(site_plugins)
        for extra_dir in extra_plugin_dirs:
            if Path(extra_dir).is_dir():
                self.plugin_manager.load_all(extra_dir)
        
        # Initialize content parser (markdown processing)
        self.content_parser = ContentParser(
            sections_dir=self.sections_dir,
            default_lang=self.default_lang,
            shortcode_processor=self.shortcode_processor,
            plugin_manager=self.plugin_manager,
        )
        
        # Initialize URL manager (navigation and path generation)
        self.url_manager = URLManager(
            languages=self.languages,
            default_lang=self.default_lang,
            config=self.config,
            get_section_page_names_fn=self._get_section_page_names,
        )
        
        # Initialize asset manager (file I/O, asset copying)
        self.asset_manager = AssetManager(
            content_dir=self.content_dir,
            sections_dir=self.sections_dir,
            data_dir=self.data_dir,
            images_dir=self.images_dir,
            assets_dir=self.assets_dir,
            files_dir=self.files_dir,
            output_dir=self.output_dir,
            default_lang=self.default_lang,
        )
        
        # Get plugin-provided Jinja2 extensions and create environment
        jinja2_exts = self.plugin_manager.get_jinja2_extensions()
        self.env = Environment(
            loader=FileSystemLoader([str(self.site_templates_dir), str(self.templates_dir)]),
            autoescape=select_autoescape(['html', 'xml']),
            extensions=jinja2_exts if jinja2_exts else [],
        )
        self.env.filters['slugify'] = self.slugify
        self.env.filters['markdown'] = self._markdown_inline
        
        # Initialize template renderer
        self.template_renderer = TemplateRenderer(site_builder=self)
        
        # Now register built-in shortcodes (template_renderer is initialized)
        register_shortcodes(self.shortcode_processor, self)
        
        # Initialize page builder
        self.page_builder = PageBuilder(self)
        
        # Initialize taxonomy manager (tags, categories, custom taxonomies)
        self.taxonomy_manager = TaxonomyManager(
            taxonomies_config=self.taxonomies,
            languages=self.languages,
            default_lang=self.default_lang,
            output_dir=self.output_dir,
            env=self.env,
            config=self.config,
            slugify_fn=self.slugify,
            get_urls_fn=self.get_urls,
            get_language_urls_fn=self.get_language_urls,
            load_data_fn=self.load_data,
            load_translations_fn=self.translation_manager.load,
            build_year=self.build_year,
            template_renderer=self.template_renderer,
        )
        
        # Initialize feed generator (RSS/Atom, sitemap)
        self.feed_generator = FeedGenerator(
            site_dir=self.site_dir,
            output_dir=self.output_dir,
            default_lang=self.default_lang,
            config=self.config,
            read_file_fn=self.read_file,
            parse_metadata_fn=self.parse_metadata,
            markdown_to_html_fn=self.markdown_to_html,
        )
    
    def get_default_language(self):
        """Get the default language code."""
        for code, lang in self.languages.items():
            if lang.get('default', False):
                return code
        # Fallback to first language
        return list(self.languages.keys())[0]
    

    def load_data(self) -> Dict[str, Any]:
        """Delegate to asset manager."""
        return self.asset_manager.load_data()
    


    def slugify(self, text):
        """Create a URL-safe slug from text. Handles Unicode."""
        text = str(text).lower().strip()
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')

    def read_file(self, filepath: Path) -> str:
        """Delegate to asset manager."""
        return self.asset_manager.read_file(filepath)
    
    def load_content_file(self, filename: str, lang: str) -> str:
        """Delegate to asset manager."""
        return self.asset_manager.load_content_file(filename, lang)
    
    def load_section_file(self, filename: str, lang: str) -> str:
        """Delegate to asset manager."""
        return self.asset_manager.load_section_file(filename, lang)

    def markdown_to_html(self, markdown_text, lang=None, current_page=None, page_depth=None, parent_name=None):
        """
        Delegate to content parser.
        Kept for backward compatibility and template filters.
        
        Args:
            markdown_text: The markdown content to convert
            lang: Language code
            current_page: Current page identifier
            page_depth: Number of directory levels deep for relative URL calculation (e.g., 0 for root, 1 for sections/page, 2 for sections/parent/child)
            parent_name: Parent page name (for nested child pages)
        """
        # Update builder's shortcode context IN-PLACE BEFORE parsing
        # This ensures shortcodes that hold a reference to builder._shortcode_ctx see the current page context
        self._shortcode_ctx.clear()
        self._shortcode_ctx.update({
            'lang': lang,
            'current_page': current_page,
            'lang_code': lang,
            'page_depth': page_depth,
            'parent_name': parent_name,
        })
        
        # Update shortcode context in content parser (in-place, preserving references held by shortcodes)
        self.content_parser.set_shortcode_context(self._shortcode_ctx)
        result = self.content_parser.markdown_to_html(markdown_text, lang, current_page)
        return result
    
    def _markdown_inline(self, text):
        """Delegate to content parser."""
        return self.content_parser._markdown_inline(text)
    
    def extract_hero_parts(self, markdown_text):
        """Delegate to content parser."""
        return self.content_parser.extract_hero_parts(markdown_text)
    
    def extract_cards(self, markdown_text):
        """Delegate to content parser."""
        return self.content_parser.extract_cards(markdown_text)
    
    def parse_metadata(self, text):
        """Delegate to content parser."""
        return self.content_parser.parse_metadata(text)
    
    def extract_excerpt(self, markdown_text, html_content):
        """Delegate to content parser."""
        return self.content_parser.extract_excerpt(markdown_text, html_content)
    
    def extract_about_parts(self, markdown_text):
        """Delegate to content parser."""
        return self.content_parser.extract_about_parts(markdown_text)
    
    def _get_section_page_names(self):
        """Return list of page names that have section: true in config."""
        return [name for name, cfg in self.config.get('pages', {}).items() if cfg.get('section')]

    def _normalize_terms(self, metadata: Dict[str, Any], tax_type: str) -> list:
        """Delegate to taxonomy manager."""
        return self.taxonomy_manager._normalize_terms(metadata, tax_type)

    def _register_taxonomy_terms(self, metadata: Dict[str, Any], lang: str) -> None:
        """Delegate to taxonomy manager."""
        self.taxonomy_manager.register_terms(metadata, lang)

    def _add_taxonomy_post(self, metadata: Dict[str, Any], lang: str, post_entry: Dict[str, Any]) -> None:
        """Delegate to taxonomy manager."""
        self.taxonomy_manager.add_post_to_terms(metadata, lang, post_entry)

    def get_posts_url_prefix(self) -> str:
        """Delegate to URL manager."""
        return self.url_manager.get_posts_url_prefix()

    def get_urls(self, current_page: str, lang: str, page_type: str = 'section') -> Dict[str, str]:
        """Delegate to URL manager."""
        return self.url_manager.get_urls(current_page, lang, page_type)
    
    def get_language_urls(self, current_page: str, current_lang: str, page_type: str = 'section', taxonomy_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Delegate to URL manager."""
        return self.url_manager.get_language_urls(current_page, current_lang, page_type, taxonomy_slug)
    
    def build_index(self, lang):
        """Build the index page for a specific language."""
        print(f"  Building index ({lang})...")
        
        # Load content
        hero_md = self.load_content_file('hero.md', lang)
        services_md = self.load_content_file('services.md', lang)
        about_md = self.load_content_file('about.md', lang)
        skills_md = self.load_content_file('skills.md', lang)
        
        # Parse content
        hero = self.extract_hero_parts(hero_md)
        services = self.extract_cards(services_md)
        about = self.extract_about_parts(about_md)
        skills = self.extract_cards(skills_md)
        
        # Build context with standard variables
        context = self.template_renderer.get_standard_context('index', lang)
        context.update({
            'page': {'title': hero['title']},
            'hero': hero,
            'services': services,
            'about': about,
            'skills': skills,
        })
        
        # Render and write
        self.template_renderer.render_and_write('index.html', context, 'index.html', lang)
    
    def _get_page_title(self, page_name):
        """Get the title of a page from config."""
        page_config = self.config.get('pages', {}).get(page_name, {})
        return page_config.get('nav_name', page_name.title())
    
    def build_posts(self, lang):
        """Build all posts for a specific language and generate blog archive."""
        posts_dir = self.site_dir / 'posts' / lang

        if not posts_dir.exists():
            return

        print(f"  Building posts ({lang})...")

        # Initialize taxonomy collection for this language
        if lang not in self.taxonomy_data:
            self.taxonomy_data[lang] = {}
        for tax_type, tax_config in self.taxonomies.items():
            if tax_config.get('enabled', True):
                if tax_type not in self.taxonomy_data[lang]:
                    self.taxonomy_data[lang][tax_type] = {}

        permalink_pattern = self.config['build'].get('permalink', 'posts/:slug')
        post_files = sorted(posts_dir.glob('*.md'), reverse=True)
        posts_list = []
        posts_prefix = self.get_posts_url_prefix()

        for post_file in post_files:
            filename = post_file.stem
            parts = filename.split('-', 3)

            if len(parts) < 4:
                print(f"    Warning: Skipping {filename} - invalid format (expected YYYY-MM-DD-slug)")
                continue

            year = parts[0]
            month = parts[1]
            day = parts[2]
            slug = parts[3]

            post_content = self.read_file(post_file)
            metadata, content_markdown = self.parse_metadata(post_content)

            if metadata.get('draft', False):
                print(f"    Skipping draft: {filename}")
                continue

            # Extract taxonomy terms from frontmatter
            self._register_taxonomy_terms(metadata, lang)

            # Extract title from metadata or markdown
            lines = content_markdown.strip().split('\n')
            if lines and lines[0].startswith('# '):
                page_title = lines[0].lstrip('# ').strip()
                content_markdown = '\n'.join(lines[1:])
            else:
                page_title = metadata.get('title', slug)

            # Run before_render_post hooks
            self.plugin_manager.run_hooks('before_render_post', {
                'slug': slug,
                'metadata': metadata,
                'content_markdown': content_markdown,
            }, lang)

            # Convert to HTML (with shortcodes and plugin extensions)
            page_content = self.markdown_to_html(content_markdown, lang=lang, current_page='post')

            excerpt = self.extract_excerpt(content_markdown, page_content)

            permalink_path = permalink_pattern
            permalink_path = permalink_path.replace(':slug', slug)
            permalink_path = permalink_path.replace(':year', year)
            permalink_path = permalink_path.replace(':month', month)
            permalink_path = permalink_path.replace(':day', day)
            permalink_path = permalink_path.rstrip('/')

            post_url = f'{slug}.html'

            # Add to posts list
            posts_list.append({
                'slug': slug,
                'title': metadata.get('title', page_title),
                'date': metadata.get('date', ''),
                'author': metadata.get('author', ''),
                'excerpt': excerpt,
                'url': post_url,
            })

            # Update taxonomy post references with correct relative URL from term page
            post_url_from_taxonomy = f'../../{posts_prefix}/{slug}.html'
            post_subtitle_html = self._markdown_inline(metadata.get('subtitle', ''))
            self._add_taxonomy_post(metadata, lang, {
                'title': metadata.get('title', page_title),
                'subtitle': post_subtitle_html,
                'slug': slug,
                'date': metadata.get('date', str(datetime.now().strftime('%Y-%m-%d'))),
                'author': metadata.get('author', ''),
                'excerpt': excerpt,
                'url': post_url_from_taxonomy,
            })

            # Build context with standard variables
            page_context = {
                'title': metadata.get('title', page_title),
                'content': page_content,
                'excerpt': excerpt,
                'date': metadata.get('date', ''),
                'author': metadata.get('author', ''),
            }
            
            context = self.template_renderer.get_standard_context(slug, lang, page_type='post')
            context.update({
                'page': page_context,
                'metadata': metadata,
            })

            # Render and write
            html = self.template_renderer.render('post.html', context)

            # Run after_render_post hooks
            self.plugin_manager.run_hooks('after_render_post', {
                'slug': slug,
                'title': page_context['title'],
                'content': page_content,
                'metadata': metadata,
            }, lang, html)

            self.template_renderer.write_output(html, f'{permalink_path}.html', lang)

        self.build_blog_archive(lang, posts_list)
    
    def build_blog_archive(self, lang, posts_list):
        """Build paginated blog archive pages."""
        if not posts_list:
            return
        
        # Check if pagination is enabled
        paginate = self.config['build'].get('paginate', True)
        posts_per_page = self.config['build'].get('posts_per_page', 5)
        
        if not paginate:
            # If pagination is disabled, build only a single page
            pages = [posts_list]
        else:
            # Split posts into pages
            pages = [posts_list[i:i + posts_per_page] for i in range(0, len(posts_list), posts_per_page)]
        
        # Get translations
        t = self.translation_manager.load(lang)
        posts_prefix = self.get_posts_url_prefix()
        
        for page_num, page_posts in enumerate(pages, 1):
            # Prepare pagination info
            total_pages = len(pages)
            pagination = {
                'current_page': page_num,
                'total_pages': total_pages,
                'has_prev': page_num > 1,
                'has_next': page_num < total_pages,
            }
            
            if page_num > 1:
                pagination['prev_url'] = f'./{posts_prefix}/' if page_num == 2 else f'./{posts_prefix}/page/{page_num - 1}/'
            
            if page_num < total_pages:
                pagination['next_url'] = f'./{posts_prefix}/page/{page_num + 1}/'
            
            # Build context with standard variables
            context = self.template_renderer.get_standard_context('blog', lang)
            context.update({
                'page': {'title': t.get('nav', {}).get('blog', 'Blog')},
                'posts': page_posts,
                'pagination': pagination if total_pages > 1 else None,
            })
            
            # Determine output path
            if page_num == 1:
                path_segments = f'{posts_prefix}/index.html'
            else:
                path_segments = f'{posts_prefix}/page/{page_num}/index.html'
            
            # Render and write
            self.template_renderer.render_and_write('blog.html', context, path_segments, lang)
    
    def build_taxonomies(self) -> None:
        """Delegate to taxonomy manager."""
        # Manager has already collected all taxonomy data during build_posts
        # Just call build_taxonomies to generate the pages
        self.taxonomy_manager.build_taxonomies()

    def clean_taxonomies(self) -> None:
        """Delegate to taxonomy manager."""
        self.taxonomy_manager.clean_directories()
    
    def copy_images(self) -> None:
        """Delegate to asset manager."""
        self.asset_manager.copy_images()
    
    def minify_css(self, css_content: str) -> str:
        """Delegate to asset manager."""
        return self.asset_manager.minify_css(css_content)
    
    def copy_assets(self) -> None:
        """Delegate to asset manager."""
        self.asset_manager.copy_assets()
    
    def copy_files(self) -> None:
        """Delegate to asset manager."""
        self.asset_manager.copy_files()
    
    def _atom_date(self, date_val: Any) -> str:
        """Delegate to feed generator."""
        return self.feed_generator._atom_date(date_val)

    def generate_rss(self) -> None:
        """Delegate to feed generator."""
        self.feed_generator.generate_rss()
    
    def generate_sitemap(self) -> None:
        """Delegate to feed generator."""
        self.feed_generator.generate_sitemap()
    
    def build(self):
        """Build the complete site."""
        print("Building website...\n")
        logger.debug("Starting build for %s", self.site_dir)

        # Run before_build hooks
        self.plugin_manager.run_hooks('before_build')

        # Ensure directories exist
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.sections_dir.mkdir(parents=True, exist_ok=True)

        if not self.templates_dir.exists():
            logger.error("Templates directory not found: %s", self.templates_dir)
            return False

        # Copy images
        try:
            self.copy_images()
        except Exception as e:
            logger.exception("Error copying images")
            return False

        # Copy and minify assets
        try:
            self.copy_assets()
        except Exception as e:
            logger.exception("Error copying assets")
            return False

        # Copy downloadable files
        try:
            self.copy_files()
        except Exception as e:
            logger.exception("Error copying files")
            return False

        # Build pages for each language
        for lang in self.languages:
            print(f"\nBuilding {self.languages[lang]['name']} ({lang}):")

            try:
                self.build_index(lang)
            except Exception as e:
                logger.exception("Error building index (%s)", lang)
                return False

            for page_name, page_config in self.config['pages'].items():
                if page_name == 'index':
                    continue
                if page_config.get('section', False):
                    try:
                        self.page_builder.build_section_page(page_name, page_config, lang)
                    except Exception as e:
                        logger.exception("Error building %s (%s)", page_name, lang)
                        return False

            try:
                self.build_posts(lang)
            except Exception as e:
                logger.exception("Error building posts (%s)", lang)
                return False

        # Clean and rebuild taxonomy pages after all posts
        try:
            self.clean_taxonomies()
        except Exception as e:
            logger.exception("Error cleaning taxonomies")
            return False
        
        try:
            self.build_taxonomies()
        except Exception as e:
            logger.exception("Error building taxonomies")
            return False

        # Generate RSS feed
        try:
            self.generate_rss()
        except Exception as e:
            logger.exception("Error generating RSS feed")
            return False

        # Generate sitemap
        try:
            self.generate_sitemap()
        except Exception as e:
            logger.exception("Error generating sitemap")
            return False

        # Run after_build hooks
        self.plugin_manager.run_hooks('after_build')

        print("\n✓ Build complete!")
        return True
