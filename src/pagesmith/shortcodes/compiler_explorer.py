"""Compiler Explorer embed shortcode."""


def compiler_explorer(args=None, kwargs=None, content=None):
    """Embeds a Compiler Explorer entry.
    
    Compiler Explorer (godbolt.org) is an interactive compiler explorer that allows
    you to see generated assembly code and compare compilers.
    
    Usage:
        {% compiler_explorer id='z6xnBq' %}
        {% compiler_explorer 'z6xnBq' %}
        {% compiler_explorer id='z6xnBq' height='600' %}
        {% compiler_explorer id='z6xnBq' height='600' width='100%' %}
    
    Args:
        id: The Compiler Explorer entry ID (required)
        height: Optional height in pixels (default: 500)
        width: Optional width as percentage or pixels (default: 100%)
    
    Returns:
        HTML iframe embed code pointing to godbolt.org
    """
    entry_id = kwargs.get('id') or (args[0] if args else '')
    if not entry_id:
        return ''
    
    height = kwargs.get('height', '500')
    width = kwargs.get('width', '100%')
    
    # Ensure height has 'px' if it's a number
    if height.isdigit():
        height = f'{height}px'
    
    return (
        f'<div class="shortcode-compiler-explorer" style="width:{width};margin:1em 0;">'
        f'<iframe src="https://godbolt.org/e/{entry_id}" '
        f'style="width:100%;height:{height};border:1px solid #ccc;" '
        f'frameborder="0" allowfullscreen></iframe></div>'
    )


# Attach name property for auto-discovery
compiler_explorer.name = 'compiler_explorer'
