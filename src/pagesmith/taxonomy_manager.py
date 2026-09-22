"""
Taxonomy management module for tags and categories.
Handles term registration, term association, and taxonomy page building.
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Callable

from jinja2 import Environment


logger = logging.getLogger(__name__)


class TaxonomyManager:
    """
    Manages taxonomy system (tags, categories, custom taxonomies).
    Tracks terms, associates posts with terms, and builds taxonomy pages.
    """
    
    def __init__(
        self,
        taxonomies_config: Dict[str, Dict[str, Any]],
        languages: Dict[str, Dict[str, Any]],
        default_lang: str,
        output_dir: Path,
        env: Environment,
        config: Dict[str, Any],
        slugify_fn: Callable[[str], str],
        get_urls_fn: Callable[[str, str], Dict[str, str]],
        get_language_urls_fn: Callable[[str, str, str, Optional[str]], list],
        load_data_fn: Callable[[], Dict[str, Any]],
        load_translations_fn: Callable[[str], Dict[str, Any]],
        build_year: int,
        template_renderer = None,
    ):
        """
        Initialize TaxonomyManager.
        
        Args:
            taxonomies_config: Taxonomy configuration from site.yaml
            languages: Languages configuration
            default_lang: Default language code
            output_dir: Output directory for generated pages
            env: Jinja2 environment for template rendering
            config: Full site config
            slugify_fn: Function to create URL-safe slugs
            get_urls_fn: Function to generate navigation URLs
            get_language_urls_fn: Function to generate language switcher URLs
            load_data_fn: Function to load YAML data
            load_translations_fn: Function to load translations
            build_year: Build timestamp year
            template_renderer: Optional TemplateRenderer instance for rendering
        """
        self.taxonomies = taxonomies_config
        self.languages = languages
        self.default_lang = default_lang
        self.output_dir = output_dir
        self.env = env
        self.config = config
        self.slugify = slugify_fn
        self.get_urls = get_urls_fn
        self.get_language_urls = get_language_urls_fn
        self.load_data = load_data_fn
        self.load_translations = load_translations_fn
        self.build_year = build_year
        self.template_renderer = template_renderer
        
        # Taxonomy data cache: lang -> taxonomy_type -> term_slug -> term_data
        self.taxonomy_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    def _normalize_terms(self, metadata: Dict[str, Any], tax_type: str) -> list:
        """
        Extract and normalize taxonomy terms for a type from page metadata.
        
        Accepts a comma-separated string or a list; anything else yields [].
        Returns a list of stripped, non-empty term names.
        
        Args:
            metadata: Page metadata dict
            tax_type: Taxonomy type key (e.g., 'tags', 'categories')
            
        Returns:
            List of normalized term names
        """
        terms = metadata.get(tax_type, [])
        if isinstance(terms, str):
            terms = [t.strip() for t in terms.split(',') if t.strip()]
        elif not isinstance(terms, list):
            terms = []
        return [str(t).strip() for t in terms if t and str(t).strip()]
    
    def register_terms(self, metadata: Dict[str, Any], lang: str) -> None:
        """
        Ensure taxonomy term entries exist for all terms in this page's metadata.
        
        Args:
            metadata: Page metadata containing term references
            lang: Language code
        """
        for tax_type, tax_config in self.taxonomies.items():
            if not tax_config.get('enabled', True):
                continue
            lang_tax = self.taxonomy_data.setdefault(lang, {})
            type_data = lang_tax.setdefault(tax_type, {})
            for term_name in self._normalize_terms(metadata, tax_type):
                term_slug = self.slugify(term_name)
                if term_slug not in type_data:
                    type_data[term_slug] = {
                        'name': term_name,
                        'slug': term_slug,
                        'count': 0,
                        'posts': [],
                    }
    
    def add_post_to_terms(self, metadata: Dict[str, Any], lang: str, post_entry: Dict[str, Any]) -> None:
        """
        Append a post/page reference to each of its taxonomy terms.
        
        Args:
            metadata: Page metadata containing term references
            lang: Language code
            post_entry: Post/page data dict to add to term listings
        """
        for tax_type, tax_config in self.taxonomies.items():
            if not tax_config.get('enabled', True):
                continue
            type_data = self.taxonomy_data.get(lang, {}).get(tax_type, {})
            for term_name in self._normalize_terms(metadata, tax_type):
                term_slug = self.slugify(term_name)
                if term_slug in type_data:
                    type_data[term_slug]['count'] += 1
                    type_data[term_slug]['posts'].append(dict(post_entry))
    
    def build_taxonomies(self) -> None:
        """Build taxonomy index and term pages for all languages."""
        logger.debug("Building taxonomies")

        for lang in self.languages:
            if lang not in self.taxonomy_data:
                continue

            lang_data = self.taxonomy_data[lang]
            if not lang_data:
                continue

            logger.debug("Building taxonomies (%s)", lang)

            t = self.load_translations(lang)
            data = self.load_data()

            for tax_type, tax_config in self.taxonomies.items():
                if not tax_config.get('enabled', True):
                    continue

                tax_slug = tax_config['slug']
                terms = lang_data.get(tax_type, {})

                sorted_terms = sorted(terms.values(), key=lambda x: x['name'].lower()) if terms else []

                plural_key = f'all_{tax_slug}' if tax_slug in ('tags', 'categories') else tax_slug
                index_title = t.get('taxonomy', {}).get(plural_key, tax_slug.capitalize())

                # --- Build taxonomy index page ---
                term_list = []
                for term in sorted_terms:
                    term_list.append({
                        'name': term['name'],
                        'slug': term['slug'],
                        'count': term['count'],
                        'url': f'./{term["slug"]}/',
                    })

                # Build context
                context = {
                    'page': {'title': index_title},
                    'taxonomy': {
                        'name': tax_type,
                        'singular': tax_config['singular'],
                        'plural': tax_config['plural'],
                        'slug': tax_slug,
                        'terms': term_list,
                    },
                    't': t,
                    'lang': self.languages[lang] | {'code': lang},
                    'languages': self.get_language_urls(tax_slug, lang, 'taxonomy'),
                    'urls': self.get_urls(tax_slug, lang),
                    'site': self.config['site'],
                    'current_page': tax_slug,
                    'year': self.build_year,
                    'data': data,
                }
                
                # Render and write
                if self.template_renderer:
                    path_segments = f'{tax_slug}/index.html'
                    self.template_renderer.render_and_write('taxonomy_index.html', context, path_segments, lang)
                else:
                    # Fallback for backward compatibility
                    html = self.env.get_template('taxonomy_index.html').render(**context)
                    if lang == self.default_lang:
                        output_path = self.output_dir / tax_slug / 'index.html'
                    else:
                        output_path = self.output_dir / lang / tax_slug / 'index.html'
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.debug("Generated %s", output_path)

                # --- Build term pages ---
                for term in sorted_terms:
                    tagged_with = t.get('taxonomy', {}).get('tagged_with', 'Posts tagged with')
                    in_category = t.get('taxonomy', {}).get('in_category', 'Posts in category')
                    page_title = f'{tagged_with} "{term["name"]}"' if tax_type == 'tags' else f'{in_category} "{term["name"]}"'

                    # Sort by date (posts), but pages without dates go to the end
                    def sort_key(item):
                        date_val = item.get('date', '')
                        if isinstance(date_val, str) and date_val:
                            return (0, date_val)  # Posts with dates come first
                        elif not isinstance(date_val, str):
                            return (0, str(date_val))  # Handle date objects
                        else:
                            return (1, '')  # Pages without dates go last
                    term_posts = sorted(term['posts'], key=sort_key, reverse=True)

                    # Build context
                    context = {
                        'page': {'title': page_title},
                        'term': {
                            'name': term['name'],
                            'slug': term['slug'],
                            'taxonomy': tax_type,
                            'count': term['count'],
                        },
                        'posts': term_posts,
                        't': t,
                        'lang': self.languages[lang] | {'code': lang},
                        'languages': self.get_language_urls(f'{tax_slug}_term', lang, 'taxonomy', term['slug']),
                        'urls': self.get_urls(f'{tax_slug}_term', lang),
                        'site': self.config['site'],
                        'current_page': tax_slug,
                        'year': self.build_year,
                        'data': data,
                    }
                    
                    # Render and write
                    if self.template_renderer:
                        path_segments = f'{tax_slug}/{term["slug"]}/index.html'
                        self.template_renderer.render_and_write('taxonomy_term.html', context, path_segments, lang)
                    else:
                        # Fallback for backward compatibility
                        html = self.env.get_template('taxonomy_term.html').render(**context)
                        if lang == self.default_lang:
                            output_path = self.output_dir / tax_slug / term['slug'] / 'index.html'
                        else:
                            output_path = self.output_dir / lang / tax_slug / term['slug'] / 'index.html'
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(html)
                        logger.debug("Generated %s", output_path)

    def _safe_rmtree(self, rel_subdir: str) -> bool:
        """
        Remove a subdirectory of output_dir, refusing paths outside output_dir.

        Guards destructive deletes against a misconfigured output_dir. If the
        path would escape output_dir the delete is skipped (returning False)
        so build continues and the stale directory is reported instead of
        risking source/user data.

        Args:
            rel_subdir: Subdirectory path relative to output_dir (e.g., 'tags')

        Returns:
            True if the directory was removed (or did not exist), False if skipped
        """
        target = self.output_dir / rel_subdir
        if not target.exists():
            return True
        if self.output_dir.resolve() not in target.resolve().parents:
            logger.error(
                "Refusing to delete %s: outside output_dir %s",
                target, self.output_dir,
            )
            return False
        shutil.rmtree(target)
        return True

    def clean_directories(self) -> None:
        """Remove all taxonomy directories from output."""
        for tax_type, tax_config in self.taxonomies.items():
            if not tax_config.get('enabled', True):
                continue
            
            tax_slug = tax_config['slug']
            
            # Clean default language taxonomy directory
            if not self._safe_rmtree(tax_slug):
                continue
            
            # Clean non-default language taxonomy directories
            for lang in self.languages:
                if lang == self.default_lang:
                    continue
                self._safe_rmtree(f'{lang}/{tax_slug}')
        
        logger.debug("Cleaned taxonomy directories")
    
    def get_data(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get all taxonomy data (for access in templates or other modules)."""
        return self.taxonomy_data
    
    def clear_cache(self) -> None:
        """Clear taxonomy data (useful before rebuild)."""
        self.taxonomy_data = {}
