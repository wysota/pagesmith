"""Child page link shortcode."""
import html


class ChildLink:
    """Creates a link to a direct child page.
    
    Usage:
        {% child_link 'consulting' label='Custom Text' %}
        {% child_link 'design_patterns/observer' %}
    
    Can include nested paths. Uses the child page's title by default, or custom label if provided.
    Works in both parent pages and child pages.
    
    Requires:
        - sections_dir set via set_context()
        - read_file_fn set via set_context()
        - parse_metadata_fn set via set_context()
        - shortcode_ctx set via set_context()
    """

    name = 'child_link'

    def __init__(self):
        self.sections_dir = None
        self.read_file_fn = None
        self.parse_metadata_fn = None
        self.shortcode_ctx = None

    def set_context(self, sections_dir, read_file_fn, parse_metadata_fn, shortcode_ctx):
        """Set the context functions and paths."""
        self.sections_dir = sections_dir
        self.read_file_fn = read_file_fn
        self.parse_metadata_fn = parse_metadata_fn
        self.shortcode_ctx = shortcode_ctx

    def __call__(self, args=None, kwargs=None, content=None):
        ctx = self.shortcode_ctx or {}
        parent_name = ctx.get('parent_name')
        current_page = ctx.get('current_page', '')
        
        if not parent_name:
            if not current_page:
                return '<!-- child_link: not available outside child pages -->'
            parent_name = current_page
        
        child_slug = args[0] if args else kwargs.get('slug', '')
        if not child_slug:
            return '<!-- child_link: child slug required -->'
        
        label = kwargs.get('label', '')
        lang = ctx.get('lang', 'en')
        
        # Read the child page's title if label not provided
        if not label:
            label = self._read_page_title(f'{parent_name}/{child_slug}', lang)
        
        # Build relative URL to the child page
        ctx_parent_name = ctx.get('parent_name')  # Original parent_name from context
        
        if ctx_parent_name and parent_name != current_page:
            # We are inside a child page; compute depth below the parent
            parent_segments = parent_name.split('/') if parent_name else []
            current_segments = current_page.split('/') if current_page else []
            relative_segments = current_segments[len(parent_segments):]
            depth = max(0, len(relative_segments) - 1)
            relative_prefix = '../' * depth
            child_url = f'{relative_prefix}{child_slug}.html'
        else:
            # We are on the parent page itself
            if parent_name and '/' in parent_name:
                # Nested parent: child is in a subdirectory named after the last segment
                child_url = f'{parent_name.split("/")[-1]}/{child_slug}.html'
            else:
                # Top-level parent: child is in a subdirectory with parent name
                child_url = f'{parent_name}/{child_slug}.html'
        
        escaped_url = html.escape(child_url, quote=True)
        escaped_label = html.escape(label)
        return f'<a href="{escaped_url}">{escaped_label}</a>'

    def _read_page_title(self, child_path, lang):
        """Read a child page's title from its markdown file."""
        if not self.sections_dir or not self.read_file_fn or not self.parse_metadata_fn:
            return child_path
        
        md_path = self.sections_dir / lang / f'{child_path}.md'
        if not md_path.exists():
            return child_path
        
        md_content = self.read_file_fn(md_path)
        if not md_content:
            return child_path
        
        metadata, _ = self.parse_metadata_fn(md_content)
        return metadata.get('title', child_path)
