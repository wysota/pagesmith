"""
Emoji markdown extension plugin.

Processes :emoji_name: syntax in markdown and converts it to actual emoji characters.

Example:
    This is :rocket: amazing!    → This is 🚀 amazing!
    Give me :thumbsup:!          → Give me 👍!
    
Emoji names are matched from the same EMOJI_MAP used by the shortcode.
"""

import re
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
import xml.etree.ElementTree as etree


# Import emoji map from the shortcode (absolute: plugins load as non-package modules)
from pagesmith.shortcodes.emoji import EMOJI_MAP


class EmojiInlineProcessor(InlineProcessor):
    """Processes :emoji_name: syntax and replaces with emoji character."""
    
    # Pattern: :word_with_underscores_or_hyphens:
    PATTERN = r':([a-zA-Z_\-]+):'
    
    def __init__(self, pattern, md, emoji_map):
        super().__init__(pattern, md)
        self.emoji_map = emoji_map
    
    def handleMatch(self, m, data):
        """Handle a matched emoji pattern."""
        emoji_name = m.group(1).lower()
        
        # Look up emoji in map
        emoji_char = self.emoji_map.get(emoji_name, None)
        
        if emoji_char:
            # Create a span element with the emoji
            el = etree.Element('span')
            el.text = emoji_char
            el.set('class', 'emoji')
            return el, m.start(0), m.end(0)
        else:
            # Not a known emoji, return None to leave it unchanged
            return None, None, None


class EmojiExtension(Extension):
    """Markdown extension for emoji support."""
    
    def extendMarkdown(self, md):
        """Register emoji inline processor with markdown."""
        processor = EmojiInlineProcessor(
            EmojiInlineProcessor.PATTERN,
            md,
            EMOJI_MAP
        )
        # Register with high priority so it processes before other inline patterns
        md.inlinePatterns.register(processor, 'emoji', 185)


def register(plugin_manager):
    """Register the emoji markdown extension."""
    emoji_ext = EmojiExtension()
    plugin_manager.add_markdown_extension(emoji_ext)
