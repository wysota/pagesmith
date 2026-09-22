"""File download shortcode."""
import html


class Download:
    """Creates a download link or card with file size.
    
    Usage:
        {% download file='archive.zip' label='Download' style='button' %}
        {% download file='data.csv' label='Data' description='Export' style='link' %}
    
    Requires: 
        - files_dir set via set_context()
        - get_urls_fn set via set_context()
        - shortcode_ctx set via set_context()
    """

    name = 'download'

    def __init__(self):
        self.files_dir = None
        self.get_urls_fn = None
        self.shortcode_ctx = None

    def set_context(self, files_dir, get_urls_fn, shortcode_ctx):
        """Set the context functions and paths."""
        self.files_dir = files_dir
        self.get_urls_fn = get_urls_fn
        self.shortcode_ctx = shortcode_ctx

    def __call__(self, args=None, kwargs=None, content=None):
        """{% download file='archive.zip' label='Download' description='...' style='button' %}"""
        file_path = kwargs.get('file', args[0] if args else '')
        if not file_path:
            return ''

        label = kwargs.get('label', file_path)
        description = kwargs.get('description', '')
        style = kwargs.get('style', 'button')

        # Read file size from disk
        size_str = ''
        if self.files_dir:
            full_path = self.files_dir / file_path
            if full_path.exists():
                size_bytes = full_path.stat().st_size
                if size_bytes < 1024:
                    size_str = f'{size_bytes} B'
                elif size_bytes < 1024 * 1024:
                    size_str = f'{size_bytes / 1024:.1f} KB'
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f'{size_bytes / (1024 * 1024):.1f} MB'
                else:
                    size_str = f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'

        # Resolve relative URL using page context
        ctx = self.shortcode_ctx or {}
        if self.get_urls_fn and ctx.get('lang') and ctx.get('current_page'):
            urls = self.get_urls_fn(ctx['current_page'], ctx['lang'])
            files_url = urls.get('files', './files')
        else:
            files_url = './files'

        file_url = f'{files_url}/{file_path}'
        escaped_url = html.escape(file_url, quote=True)
        escaped_label = html.escape(label)

        if style == 'link':
            size_attr = f' ({size_str})' if size_str else ''
            return f'<a href="{escaped_url}" download>{escaped_label}</a>{size_attr}'
        else:
            size_html = f'<span class="download-size">{size_str}</span>' if size_str else ''
            desc_html = f'<p class="download-description">{html.escape(description)}</p>' if description else ''
            return (
                f'<a href="{escaped_url}" class="download-card" download>'
                f'<span class="download-icon">&#128229;</span>'
                f'<span class="download-info">'
                f'<span class="download-label">{escaped_label}</span>'
                f'{size_html}'
                f'</span>'
                f'{desc_html}'
                f'</a>'
            )
