"""Code highlight shortcode."""


def highlight(args=None, kwargs=None, content=None):
    """Renders a code block with optional language highlighting.
    
    Usage:
        {% highlight lang='python' %}
        def hello():
            print("world")
        {% endhighlight %}
    """
    import html
    lang = kwargs.get('lang', kwargs.get('language', ''))
    if not content:
        return ''
    code = html.escape(content)
    lang_class = f' class="language-{lang}"' if lang else ''
    return f'<pre><code{lang_class}>{code}</code></pre>'


# Attach name property for auto-discovery
highlight.name = 'highlight'
