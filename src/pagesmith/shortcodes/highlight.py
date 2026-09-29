"""Code highlight shortcode."""

from markdown.extensions.codehilite import CodeHilite


def highlight(args=None, kwargs=None, content=None):
    """Renders a code block with Pygments syntax highlighting.

    Usage:
        {% highlight lang='python' %}
        def hello():
            print("world")
        {% endhighlight %}

    The language can be given as ``lang``/``language`` keyword or as the first
    positional argument. When omitted, Pygments guesses the language (falling
    back to plain text). ``CodeHilite`` escapes the code and degrades to a
    plain ``<pre><code>`` block when Pygments is unavailable.
    """
    if not content:
        return ''

    args = args or []
    kwargs = kwargs or {}
    lang = kwargs.get('lang', kwargs.get('language', ''))
    if not lang and args:
        lang = args[0]

    code = content.strip('\n')

    hilite = CodeHilite(
        code,
        lang=lang or None,
        cssclass='codehilite',
        guess_lang=True,
    )
    return hilite.hilite()


# Attach name property for auto-discovery
highlight.name = 'highlight'
