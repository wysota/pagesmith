"""YouTube embed shortcode."""


def youtube(args=None, kwargs=None, content=None):
    """Embeds a YouTube video.
    
    Usage:
        {% youtube id='dQw4w9WgXcQ' %}
        {% youtube 'dQw4w9WgXcQ' %}
    """
    video_id = kwargs.get('id') or (args[0] if args else '')
    if not video_id:
        return ''
    return (
        '<div class="shortcode-video" style="position:relative;padding-bottom:56.25%;'
        'height:0;overflow:hidden;max-width:100%;">'
        f'<iframe src="https://www.youtube.com/embed/{video_id}" '
        'frameborder="0" allowfullscreen '
        'style="position:absolute;top:0;left:0;width:100%;height:100%;"></iframe></div>'
    )


# Attach name property for auto-discovery
youtube.name = 'youtube'
