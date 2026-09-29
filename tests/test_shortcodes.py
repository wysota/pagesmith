#!/usr/bin/env python3
"""Unit tests for built-in shortcodes (focusing on `highlight`)."""

import tempfile
import unittest
from pathlib import Path

from pagesmith.content_parser import ContentParser
from pagesmith.plugins.shortcodes import ShortcodeProcessor
from pagesmith.shortcodes import get_all_shortcodes
from pagesmith.shortcodes.highlight import highlight


PYTHON_SNIPPET = (
    'import os\n'
    '\n'
    'class Foo(object):\n'
    '    def bar(self, x):\n'
    '        return os.path.join(x, "y")\n'
)


class DummyPluginManager:
    def get_markdown_extensions(self):
        return []

    def run_filter_hooks(self, hook_name, value, *args, **kwargs):
        return value


class TestHighlightShortcode(unittest.TestCase):

    def test_empty_content(self):
        self.assertEqual(highlight(kwargs={}, content=''), '')

    def test_explicit_language_highlighted(self):
        html = highlight(kwargs={'lang': 'python'}, content=PYTHON_SNIPPET)
        self.assertIn('codehilite', html)
        self.assertIn('<span class="', html)

    def test_language_keyword_alias(self):
        html = highlight(kwargs={'language': 'python'}, content=PYTHON_SNIPPET)
        self.assertIn('<span class="', html)

    def test_positional_language(self):
        html = highlight(args=['python'], kwargs={}, content=PYTHON_SNIPPET)
        self.assertIn('<span class="', html)

    def test_guesses_language_when_omitted(self):
        html = highlight(kwargs={}, content=PYTHON_SNIPPET)
        self.assertIn('codehilite', html)
        self.assertIn('<span class="', html)

    def test_escapes_html_when_unhighlighted(self):
        # Plain text is not a guessable language; the markup must still escape.
        html = highlight(kwargs={'lang': 'text'}, content='<script>alert(1)</script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)


class TestHighlightIntegration(unittest.TestCase):
    """The shortcode output must survive markdown conversion intact."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        sections_dir = Path(self.temp_dir) / 'sections'
        sections_dir.mkdir(exist_ok=True)

        processor = ShortcodeProcessor()
        for name, handler in get_all_shortcodes().items():
            processor.register(name, handler)

        self.parser = ContentParser(
            sections_dir=sections_dir,
            default_lang='en',
            shortcode_processor=processor,
            plugin_manager=DummyPluginManager(),
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shortcode_renders_highlighted_block(self):
        markdown = "{% highlight lang='python' %}\n" + PYTHON_SNIPPET + "{% endhighlight %}"
        html = self.parser.markdown_to_html(markdown, lang='en', current_page='test')
        self.assertIn('<div class="codehilite">', html)
        self.assertIn('<span class="', html)

    def test_unlabeled_fenced_block_is_guessed(self):
        markdown = '```\n' + PYTHON_SNIPPET + '```'
        html = self.parser.markdown_to_html(markdown, lang='en', current_page='test')
        self.assertIn('<span class="', html)


if __name__ == '__main__':
    unittest.main()
