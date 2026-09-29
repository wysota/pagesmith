#!/usr/bin/env python3
"""Unit tests for ContentParser (metadata, markdown, content extraction)."""

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pagesmith.content_parser import ContentParser


class DummyShortcodeProcessor:
    """Minimal shortcode processor that passes text through unchanged."""

    def process(self, text):
        return text


class DummyPluginManager:
    """Minimal plugin manager providing the extensions/hooks ContentParser uses."""

    def get_markdown_extensions(self):
        return []

    def run_filter_hooks(self, hook_name, value, *args, **kwargs):
        return value


def make_parser():
    temp_dir = tempfile.mkdtemp()
    sections_dir = Path(temp_dir) / 'sections'
    sections_dir.mkdir(exist_ok=True)
    parser = ContentParser(
        sections_dir=sections_dir,
        default_lang='en',
        shortcode_processor=DummyShortcodeProcessor(),
        plugin_manager=DummyPluginManager(),
    )
    return parser, temp_dir


class TestParseMetadata(unittest.TestCase):

    def setUp(self):
        self.parser, self.temp_dir = make_parser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_without_metadata(self):
        content = "# Hello\n\nSome content."
        metadata, body = self.parser.parse_metadata(content)
        self.assertEqual(metadata, {})
        self.assertEqual(body, content)

    def test_with_yaml_metadata(self):
        content = (
            "---\n"
            "title: Test Page\n"
            "date: 2026-08-20\n"
            "draft: false\n"
            "---\n"
            "# Test Page\n\nContent here."
        )
        metadata, body = self.parser.parse_metadata(content)
        self.assertEqual(metadata['title'], 'Test Page')
        self.assertEqual(metadata['date'], date(2026, 8, 20))
        self.assertEqual(metadata['draft'], False)
        self.assertIn('# Test Page', body)
        self.assertIn('Content here', body)

    def test_unclosed_metadata(self):
        content = "---\ntitle: Test\n\nSome content."
        metadata, body = self.parser.parse_metadata(content)
        self.assertEqual(metadata, {})
        self.assertEqual(body, content)


class TestMarkdownToHtml(unittest.TestCase):

    def setUp(self):
        self.parser, self.temp_dir = make_parser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty(self):
        self.assertEqual(self.parser.markdown_to_html('', lang='en', current_page='test'), '')

    def test_heading_and_paragraph(self):
        html = self.parser.markdown_to_html("# Heading\n\nParagraph.", lang='en', current_page='test')
        self.assertIn('<h1', html)
        self.assertIn('Paragraph', html)

    def test_bold_and_italic(self):
        html = self.parser.markdown_to_html("**bold** and *italic*", lang='en', current_page='test')
        self.assertIn('<strong>', html)
        self.assertIn('<em>', html)

    def test_list(self):
        html = self.parser.markdown_to_html("- Item 1\n- Item 2", lang='en', current_page='test')
        self.assertIn('<ul>', html)
        self.assertIn('<li>', html)

    def test_link(self):
        html = self.parser.markdown_to_html("[Link](https://example.com)", lang='en', current_page='test')
        self.assertIn('<a', html)
        self.assertIn('https://example.com', html)


class TestExtractHeroParts(unittest.TestCase):

    def setUp(self):
        self.parser, self.temp_dir = make_parser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_two_lines(self):
        hero = self.parser.extract_hero_parts("# Title\n\nSubtitle text\n\nRest")
        self.assertEqual(hero['title'], 'Title')
        self.assertEqual(hero['subtitle'], 'Subtitle text')

    def test_two_lines_without_heading(self):
        hero = self.parser.extract_hero_parts("Title\n\nSubtitle text\n\nRest")
        self.assertEqual(hero['title'], 'Title')
        self.assertEqual(hero['subtitle'], 'Subtitle text')

    def test_single_line(self):
        hero = self.parser.extract_hero_parts("Only title")
        self.assertEqual(hero['title'], 'Only title')
        self.assertEqual(hero['subtitle'], '')


class TestExtractCards(unittest.TestCase):

    def setUp(self):
        self.parser, self.temp_dir = make_parser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_cards(self):
        cards = self.parser.extract_cards("- **T1**: Desc 1\n- **T2**: Desc 2")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0], {'title': 'T1', 'description': 'Desc 1'})
        self.assertEqual(cards[1], {'title': 'T2', 'description': 'Desc 2'})

    def test_ignores_non_card_lines(self):
        cards = self.parser.extract_cards("Plain line\n- **T**: Desc")
        self.assertEqual(len(cards), 1)


class TestExtractTitleFromMarkdown(unittest.TestCase):

    def setUp(self):
        self.parser, self.temp_dir = make_parser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_from_heading(self):
        title, content = self.parser.extract_title_from_markdown(
            "# My Title\n\nBody", {}, fallback='fb'
        )
        self.assertEqual(title, 'My Title')
        self.assertIn('Body', content)
        self.assertNotIn('# My Title', content)

    def test_from_metadata(self):
        title, content = self.parser.extract_title_from_markdown(
            "Body text", {'title': 'From Meta'}, fallback='fb'
        )
        self.assertEqual(title, 'From Meta')
        self.assertEqual(content, 'Body text')

    def test_from_fallback(self):
        title, content = self.parser.extract_title_from_markdown('', {}, fallback='Fallback')
        self.assertEqual(title, 'Fallback')
        self.assertEqual(content, '')


if __name__ == '__main__':
    unittest.main()