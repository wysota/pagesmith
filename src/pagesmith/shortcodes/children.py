"""Child pages list shortcode."""
import fnmatch
import html


class Children:
    """Lists all child pages or child pages matching a pattern.
    
    Usage:
        {% children %}
        {% children pattern='services-*' %}
        {% children template='custom' %}
    
    Pattern uses shell-style wildcards (* and ?).
    Works in both parent pages and child pages.
    
    Parameters:
        pattern - Shell-style pattern for child slugs (* and ?). Default: '*'
        template - Jinja2 template partial for rendering. Default: 'children'
                  Set to 'default' to use inline HTML rendering (backward compatible).
                  Custom templates receive: children (list), parent_name, current_page
    
    Requires:
        - sections_dir set via set_context()
        - read_file_fn set via set_context()
        - parse_metadata_fn set via set_context()
        - render_fn set via set_context()
        - shortcode_ctx set via set_context()
    """

    name = 'children'

    def __init__(self):
        self.sections_dir = None
        self.read_file_fn = None
        self.parse_metadata_fn = None
        self.render_fn = None
        self.shortcode_ctx = None

    def set_context(self, sections_dir, read_file_fn, parse_metadata_fn, render_fn, shortcode_ctx):
        """Set the context functions and paths."""
        self.sections_dir = sections_dir
        self.read_file_fn = read_file_fn
        self.parse_metadata_fn = parse_metadata_fn
        self.render_fn = render_fn
        self.shortcode_ctx = shortcode_ctx

    def __call__(self, args=None, kwargs=None, content=None):
        ctx = self.shortcode_ctx or {}
        
        pattern = kwargs.get('pattern', '*')
        template_name = kwargs.get('template', 'children')
        lang = ctx.get('lang', 'en')
        current_page = ctx.get('current_page', '')
        parent_name = ctx.get('parent_name')
        
        # Determine the parent page and child directory
        if not parent_name:
            # Top-level parent page: current_page IS the parent, no /
            parent_name = current_page
            child_path = ''
            child_dir = self.sections_dir / lang / parent_name
            relative_prefix = f'{parent_name}/'  # Children in parent directory
        elif parent_name == current_page:
            # current_page is a nested parent (e.g., design_patterns/observer)
            # and it has children (cpp, function_based, etc.)
            child_path = ''
            child_dir = self.sections_dir / lang / parent_name
            # Children are in a subdirectory named after the last segment
            relative_prefix = current_page.split('/')[-1] + '/' if '/' in current_page else ''
        else:
            # current_page is a child: extract path after parent_name
            if current_page.startswith(parent_name + '/'):
                child_path = current_page[len(parent_name) + 1:]
            else:
                child_path = ''
            
            if child_path:
                child_dir = self.sections_dir / lang / parent_name / child_path
                # For child pages, children are in a subdirectory with the same name as current page
                relative_prefix = f'{child_path.split("/")[-1]}/'
            else:
                child_dir = self.sections_dir / lang / parent_name
                relative_prefix = ''
        
        if not child_dir.exists():
            return ''
        
        children = []
        for md_file in sorted(child_dir.glob('*.md')):
            child_slug = md_file.stem
            
            # Match against pattern
            if not fnmatch.fnmatch(child_slug, pattern):
                continue
            
            md_content = self.read_file_fn(md_file)
            if not md_content:
                continue
            
            metadata, _ = self.parse_metadata_fn(md_content)
            child_title = metadata.get('title', child_slug)
            child_url = f'{relative_prefix}{child_slug}.html'
            
            children.append({
                'slug': child_slug,
                'title': child_title,
                'url': child_url,
                'order': metadata.get('child_order', 999),
            })
        
        # Sort by child_order
        children.sort(key=lambda x: x['order'])
        
        if not children:
            return ''
        
        # Use template if specified and not 'default'
        if template_name and template_name != 'default' and self.render_fn:
            try:
                context = {
                    'children': children,
                    'parent_name': parent_name,
                    'current_page': current_page,
                }
                return self.render_fn(f'partials/{template_name}.html', context)
            except Exception as e:
                return f'<!-- Shortcode "children" template error: {e} -->'
        
        # Fallback: inline HTML rendering (backward compatible)
        html_result = '<ul class="children-list">\n'
        for child in children:
            escaped_url = html.escape(child['url'], quote=True)
            escaped_title = html.escape(child['title'])
            html_result += f'  <li><a href="{escaped_url}">{escaped_title}</a></li>\n'
        html_result += '</ul>'
        
        return html_result
