import re


class ShortcodeProcessor:
    """Processes shortcodes in markdown content before HTML conversion.

    Supports two forms:
      Self-closing: {% name arg1 key="val" %}
      Block:        {% name %}content{% endname %}
    """

    BLOCK_RE = re.compile(
        r'\{%\s*(\w+)\s*(.*?)\s*%\}\n?(.*?)\n?\{%\s*end\1\s*%\}',
        re.DOTALL
    )
    INLINE_RE = re.compile(r'\{%\s*(\w+)\s*(.*?)\s*%\}')

    def __init__(self):
        self.registry = {}

    def register(self, name, handler):
        """Register a shortcode handler.

        handler signature: handler(args=None, kwargs=None, content=None) -> str
        """
        self.registry[name] = handler

    def process(self, text):
        """Process all shortcodes in text, returning HTML with shortcodes replaced."""
        if not text:
            return text

        text = self.BLOCK_RE.sub(self._replace_block, text)
        text = self.INLINE_RE.sub(self._replace_inline, text)
        return text

    def _parse_args(self, arg_string):
        """Parse shortcode argument string into positional and keyword arguments."""
        args = []
        kwargs = {}
        if not arg_string:
            return args, kwargs

        # Pattern breakdown:
        # 1. "..." - double-quoted string (positional arg)
        # 2. '...' - single-quoted string (positional arg)
        # 3. key="..." - key with double-quoted value
        # 4. key='...' - key with single-quoted value
        # 5. key=value - key with unquoted value (non-space chars)
        # 6. \S+ - unquoted word (positional arg)
        pattern = r'(?:"([^"]*)"|\'([^\']*)\'|(\S+)="([^"]*)"|(\S+)=\'([^\']*)\'|(\S+)=(\S+)|(\S+))'
        for match in re.finditer(pattern, arg_string.strip()):
            groups = match.groups()
            if groups[0]:  # "..."
                args.append(groups[0])
            elif groups[1]:  # '...'
                args.append(groups[1])
            elif groups[2] and groups[3]:  # key="..."
                kwargs[groups[2]] = groups[3]
            elif groups[4] and groups[5]:  # key='...'
                kwargs[groups[4]] = groups[5]
            elif groups[6] and groups[7]:  # key=value
                kwargs[groups[6]] = groups[7]
            elif groups[8]:  # unquoted word
                args.append(groups[8])

        return args, kwargs

    def _replace_block(self, match):
        name = match.group(1)
        arg_string = match.group(2)
        content = match.group(3)
        args, kwargs = self._parse_args(arg_string)

        handler = self.registry.get(name)
        if not handler:
            return match.group(0)

        try:
            return handler(args=args, kwargs=kwargs, content=content)
        except Exception as e:
            return f'<!-- Shortcode "{name}" error: {e} -->'

    def _replace_inline(self, match):
        name = match.group(1)
        arg_string = match.group(2)
        args, kwargs = self._parse_args(arg_string)

        handler = self.registry.get(name)
        if not handler:
            return match.group(0)

        try:
            return handler(args=args, kwargs=kwargs)
        except Exception as e:
            return f'<!-- Shortcode "{name}" error: {e} -->'
