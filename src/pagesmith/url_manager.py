"""
URL generation and navigation management for multi-language sites.
Handles relative path calculation, language-aware URLs, and site structure mapping.
"""

from typing import Dict, Optional, Any, List


class URLManager:
    """
    Manages URL generation for different page types and languages.
    Calculates relative paths, generates language switcher URLs, and maintains navigation structure.
    """
    
    def __init__(
        self,
        languages: Dict[str, Dict[str, Any]],
        default_lang: str,
        config: Dict[str, Any],
        get_section_page_names_fn,
    ):
        """
        Initialize URLManager.
        
        Args:
            languages: Dict of language configs from site.yaml
            default_lang: Default language code (e.g., 'en')
            config: Full site config (needed for build settings)
            get_section_page_names_fn: Function that returns list of section page names
        """
        self.languages = languages
        self.default_lang = default_lang
        self.config = config
        self._get_section_page_names = get_section_page_names_fn
    
    def get_posts_url_prefix(self) -> str:
        """
        Extract the directory prefix from the permalink pattern.
        
        Returns:
            URL prefix for posts directory (e.g., 'posts', 'blog', etc.)
        """
        permalink = self.config['build'].get('permalink', 'posts/:slug')
        # Get everything up to the last placeholder
        parts = permalink.split('/')
        # Remove the last part if it contains a placeholder
        if parts[-1].startswith(':'):
            parts = parts[:-1]
        return '/'.join(parts) if parts else 'posts'
    
    def _build_url_set(
        self,
        *,
        home: str,
        root_prefix: str,
        lang_prefix: str,
        section_tmpl: str,
        posts: Optional[str] = None,
        blog: Optional[str] = None,
        tags: Optional[str] = None,
        categories: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Assemble a navigation URL dict from computed path prefixes.

        Args:
            home: URL pointing at the language home (index).
            root_prefix: '../'-style prefix reaching the site root (for
                images/files/assets/posts which are not language-scoped).
            lang_prefix: '../'-style prefix reaching the language root (for
                language-scoped taxonomies tags/categories).
            section_tmpl: format string for section pages, with a '{p}'
                placeholder for the page name.
            posts: optional explicit override for posts URL
            blog: optional explicit override for blog URL
            tags: optional explicit override for tags URL
            categories: optional explicit override for categories URL

        Returns:
            Dict mapping URL key names to relative URLs
        """
        posts_prefix = self.get_posts_url_prefix()
        posts_url = posts if posts is not None else f'{root_prefix}{posts_prefix}'
        blog_url = blog if blog is not None else posts_url
        tags_url = tags if tags is not None else f'{lang_prefix}tags/'
        categories_url = categories if categories is not None else f'{lang_prefix}categories/'

        result = {
            'home': home,
            'images': f'{root_prefix}images',
            'files': f'{root_prefix}files',
            'posts': posts_url,
            'blog': blog_url,
            'assets': f'{root_prefix}assets',
            'tags': tags_url,
            'categories': categories_url,
        }
        for p in self._get_section_page_names():
            result[p] = section_tmpl.format(p=p)
        return result

    def get_urls(self, current_page: str, lang: str, page_type: str = 'section') -> Dict[str, str]:
        """
        Generate URLs for navigation based on page location and language.
        
        Args:
            current_page: Page identifier (e.g., 'index', 'contact', 'post', 'tags')
            lang: Language code (e.g., 'en', 'pl')
            page_type: Type of page ('section', 'post'). Distinguishes a post slug
                (which renders into the posts directory) from a section page.
            
        Returns:
            Dict of URLs for use in templates (home, images, sections/*, etc.)
        """
        is_default_lang = (lang == self.default_lang)
        is_index = (current_page == 'index')
        is_blog = (current_page == 'blog')
        is_post = (current_page == 'post' or page_type == 'post')
        is_taxonomy_index = current_page in ('tags', 'categories')
        is_taxonomy_term = current_page in ('tags_term', 'categories_term')
        is_child_page = '/' in current_page
        posts_prefix = self.get_posts_url_prefix()

        # Child pages (nested under parent sections). Non-default languages also
        # have one extra directory level (the language dir) to traverse.
        if is_child_page:
            depth = current_page.count('/')
            if is_default_lang:
                up = '../' * depth
                root_up = '../' * (depth + 1)
                return self._build_url_set(
                    home=root_up, root_prefix=root_up, lang_prefix=root_up,
                    section_tmpl=f'{up}{{p}}.html')
            up = '../' * depth
            up_lang = '../' * (depth + 1)
            root_up = '../' * (depth + 2)
            return self._build_url_set(
                home=up_lang, root_prefix=root_up, lang_prefix=up_lang,
                section_tmpl=f'{up}{{p}}.html')

        # Single post pages live at {posts_prefix}/slug.html, not in sections/
        if is_post:
            up = '../' * (posts_prefix.count('/') + 1)
            root_up = up if is_default_lang else up + '../'
            return self._build_url_set(
                home=up, root_prefix=root_up, lang_prefix=up,
                section_tmpl=f'{up}sections/{{p}}.html',
                posts='./', blog='./')

        # Taxonomy term pages are one level deeper than taxonomy index
        if is_taxonomy_term:
            if is_default_lang:
                return self._build_url_set(
                    home='../../', root_prefix='../../', lang_prefix='../../',
                    section_tmpl='../../sections/{p}.html')
            return self._build_url_set(
                home='../../../', root_prefix='../../../', lang_prefix='../../../',
                section_tmpl='../../../sections/{p}.html')

        # Taxonomy index pages (tags/, categories/)
        if is_taxonomy_index:
            if is_default_lang:
                return self._build_url_set(
                    home='../', root_prefix='../', lang_prefix='../',
                    section_tmpl='../sections/{p}.html',
                    tags='./', categories='./')
            return self._build_url_set(
                home='../', root_prefix='../../', lang_prefix='../../',
                section_tmpl='../sections/{p}.html',
                tags='./', categories='./')

        if is_default_lang:
            if is_index:
                return self._build_url_set(
                    home='./', root_prefix='./', lang_prefix='./',
                    section_tmpl='./sections/{p}.html')
            if is_blog:
                return self._build_url_set(
                    home='../', root_prefix='../', lang_prefix='../',
                    section_tmpl='../sections/{p}.html',
                    blog='./')
            # Top-level section page (default language)
            return self._build_url_set(
                home='../', root_prefix='../', lang_prefix='../',
                section_tmpl='./{p}.html')
        else:
            if is_index:
                return self._build_url_set(
                    home='./', root_prefix='../', lang_prefix='./',
                    section_tmpl='./sections/{p}.html',
                    posts=f'./{posts_prefix}', blog=f'./{posts_prefix}')
            if is_blog:
                return self._build_url_set(
                    home='../../', root_prefix='../../', lang_prefix='../../',
                    section_tmpl='../../sections/{p}.html',
                    blog='./')
            # Top-level section page (non-default language)
            return self._build_url_set(
                home='../', root_prefix='../../', lang_prefix='../',
                section_tmpl='./{p}.html')

    def get_language_urls(
        self,
        current_page: str,
        current_lang: str,
        page_type: str = 'section',
        taxonomy_slug: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate URLs for language switcher.
        
        Args:
            current_page: Current page identifier
            current_lang: Current language code
            page_type: Type of page ('section', 'post', etc.)
            taxonomy_slug: Slug of taxonomy term (if on taxonomy page)
            
        Returns:
            List of language dicts with code, name, page_url, is_default
        """
        lang_urls = []
        posts_prefix = self.get_posts_url_prefix()
        is_child_page = '/' in current_page

        is_taxonomy_index = current_page in ('tags', 'categories')
        is_taxonomy_term = current_page in ('tags_term', 'categories_term')
        tax_type = None
        if is_taxonomy_index:
            tax_type = current_page
        elif is_taxonomy_term:
            tax_type = current_page.replace('_term', '')

        for code, lang_config in self.languages.items():
            is_default = (code == self.default_lang)

            if is_child_page:
                # Child pages can be nested (parent/child or deeper)
                depth = current_page.count('/')
                # Compute prefix to reach root from current page location
                if current_lang == self.default_lang:
                    up = '../' * (depth + 1)
                else:
                    up = '../' * (depth + 2)
                if is_default:
                    if current_lang == self.default_lang:
                        url = f'./{current_page.rsplit("/", 1)[-1]}.html'
                    else:
                        url = f'{up}sections/{current_page}.html'
                else:
                    if current_lang == self.default_lang:
                        url = f'{up}{code}/sections/{current_page}.html'
                    elif current_lang == code:
                        url = f'./{current_page.rsplit("/", 1)[-1]}.html'
                    else:
                        url = f'{up}{code}/sections/{current_page}.html'
            elif is_taxonomy_index or is_taxonomy_term:
                tax_dir = tax_type
                if is_taxonomy_term:
                    if current_lang == code:
                        url = './'
                    elif is_default:
                        # Link to the taxonomy index in the other language:
                        # the translated term may use a different slug, and the
                        # index is always a valid target.
                        url = f'../../../{tax_dir}/'
                    else:
                        if current_lang == self.default_lang:
                            url = f'../../{code}/{tax_dir}/'
                        else:
                            url = f'../../../{code}/{tax_dir}/'
                else:
                    if current_lang == code:
                        url = './'
                    elif is_default:
                        url = f'../../{tax_dir}/'
                    else:
                        if current_lang == self.default_lang:
                            url = f'../{code}/{tax_dir}/'
                        else:
                            url = f'../../{code}/{tax_dir}/'
            elif current_page == 'index':
                if is_default:
                    if current_lang == self.default_lang:
                        url = './'
                    else:
                        url = '../'
                else:
                    if current_lang == self.default_lang:
                        url = f'./{code}/'
                    elif current_lang == code:
                        url = './'
                    else:
                        url = f'../{code}/'
            elif current_page == 'blog':
                if current_lang == code:
                    url = './'
                elif is_default:
                    url = f'../../{posts_prefix}/'
                else:
                    if current_lang == self.default_lang:
                        url = f'../{code}/{posts_prefix}/'
                    else:
                        url = f'../../{code}/{posts_prefix}/'
            else:
                dir_name = posts_prefix if page_type == 'post' else 'sections'
                if is_default:
                    if current_lang == self.default_lang:
                        url = f'./{current_page}.html'
                    else:
                        url = f'../../{dir_name}/{current_page}.html'
                else:
                    if current_lang == self.default_lang:
                        url = f'../{code}/{dir_name}/{current_page}.html'
                    elif current_lang == code:
                        url = f'./{current_page}.html'
                    else:
                        url = f'../../{code}/{dir_name}/{current_page}.html'

            lang_urls.append({
                'code': code,
                'name': lang_config['name'],
                'page_url': url,
                'is_default': is_default
            })

        return lang_urls
