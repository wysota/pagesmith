"""Figure image shortcode."""


def figure(args=None, kwargs=None, content=None):
    """Embeds an image with optional caption.
    
    Usage:
        {% figure src='image.jpg' caption='Image caption' alt='Alt text' class='my-class' %}
    """
    import html
    src = kwargs.get('src', '')
    caption = kwargs.get('caption', '')
    alt = kwargs.get('alt', caption)
    cls = kwargs.get('class', 'shortcode-figure')
    if not src:
        return ''
    result = f'<figure class="{cls}"><img src="{src}" alt="{alt}" />'
    if caption:
        result += f'<figcaption>{caption}</figcaption>'
    result += '</figure>'
    return result


# Attach name property for auto-discovery
figure.name = 'figure'
