"""GitHub Gist embed shortcode."""


def gist(args=None, kwargs=None, content=None):
    """Embeds a GitHub Gist.
    
    Usage:
        {% gist id='abc123xyz' %}
        {% gist id='abc123xyz' file='main.py' %}
        {% gist 'abc123xyz' %}
    """
    gist_id = kwargs.get('id') or (args[0] if args else '')
    if not gist_id:
        return ''
    file_arg = kwargs.get('file', '')
    file_suffix = f'?file={file_arg}' if file_arg else ''
    return f'<script src="https://gist.github.com/{gist_id}.js{file_suffix}"></script>'


# Attach name property for auto-discovery
gist.name = 'gist'
