"""Tests for data-driven index page composition via ``pages.index.content_files``.

Covers the three configuration forms:
- plain Markdown (simple default site),
- bare-string entries using the classic name->format convention,
- explicit ``name: {file, format}`` mapping.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from pagesmith.builder import SiteBuilder


def _make_site(root, name, pages_cfg, files):
    """Create a minimal site directory and return its path."""
    site = root / name
    (site / 'config').mkdir(parents=True)
    (site / 'content' / 'en').mkdir(parents=True)
    (site / 'translations').mkdir(parents=True)
    (site / 'assets' / 'css').mkdir(parents=True)
    (site / 'assets').mkdir(parents=True, exist_ok=True)

    config = {
        'site': {'name': name.title(), 'base_url': f'https://{name}.example.com'},
        'languages': {'en': {'name': 'English', 'code': 'en', 'default': True}},
        'pages': {'index': {'template': 'index.html', **pages_cfg}},
    }
    (site / 'config' / 'site.yaml').write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding='utf-8',
    )

    # Minimal assets so the shared base template resolves.
    (site / 'assets' / 'css' / 'style.css').write_text('body {}\n', encoding='utf-8')
    (site / 'assets' / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding='utf-8')

    # Minimal UI strings.
    (site / 'translations' / 'en.yaml').write_text(
        'footer:\n  copyright: All rights reserved.\n', encoding='utf-8')

    for rel, content in files.items():
        path = site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    return site


class TestIndexComposition(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, name, pages_cfg, files):
        site = _make_site(self.root, name, pages_cfg, files)
        out = self.root / f'out-{name}'
        builder = SiteBuilder(site, str(out))
        self.assertTrue(builder.build(), f"build failed for {name}")
        index = (out / 'index.html').read_text(encoding='utf-8')
        return index

    def test_plain_markdown_form(self):
        """A single Markdown file provides title and page content."""
        index = self._build('plain', {'content_files': ['index.md']}, {
            'content/en/index.md': '# Plain Site\n\nSome **placeholder** body text.\n',
        })
        self.assertIn('Plain Site', index)
        self.assertIn('<strong>placeholder</strong>', index)
        self.assertIn('<h1>Plain Site</h1>', index)
        # No hero/cards sections rendered.
        self.assertNotIn('service-card', index)

    def test_bare_string_convention_form(self):
        """The classic hero layout still works via plain file names."""
        index = self._build('classic', {'content_files': ['hero.md', 'services.md', 'about.md', 'skills.md']}, {
            'content/en/hero.md': '# Classic\n\nTagline here.\n',
            'content/en/services.md': '- **One**: First service\n- **Two**: Second service\n',
            'content/en/about.md': '# About\n\nShort intro.\n\n- Expert skill\n',
            'content/en/skills.md': '- **Ruby**: Programming\n',
        })
        self.assertIn('<h1>Classic</h1>', index)
        self.assertIn('Tagline here.', index)
        self.assertIn('service-card', index)
        self.assertIn('First service', index)
        self.assertIn('Second service', index)
        self.assertIn('<li>Expert skill</li>', index)
        self.assertIn('skill-item', index)
        self.assertIn('Ruby', index)

    def test_explicit_mapping_form(self):
        """Explicit name/file/format mapping gives full control."""
        pages_cfg = {
            'content_files': [
                {'hero': {'file': 'headline.md', 'format': 'hero'}},
                {'services': {'file': 'feature-list.md', 'format': 'cards'}},
            ],
        }
        index = self._build('mapped', pages_cfg, {
            'content/en/headline.md': '# Mapped Hero\n\nSub line.\n',
            'content/en/feature-list.md': '- **Alpha**: A thing\n- **Beta**: B thing\n',
        })
        self.assertIn('<h1>Mapped Hero</h1>', index)
        self.assertIn('Sub line.', index)
        self.assertIn('Alpha', index)
        self.assertIn('B thing', index)
        # The actual file names differ from the section keys; the mapping
        # keys are what the template sees.
        self.assertIn('service-card', index)

    def test_custom_section_names_with_site_template(self):
        """Arbitrary section names are exposed to templates; a per-site
        template override renders them however it likes."""
        self._build('custom', {
            'content_files': [
                {'headline': {'file': 'head.md', 'format': 'hero'}},
                {'boxes': {'file': 'boxes.md', 'format': 'cards'}},
            ],
        }, {
            'content/en/head.md': 'Custom Hero\n\nSub here.\n',
            'content/en/boxes.md': '- **BoxA**: Alpha content\n- **BoxB**: Beta content\n',
            'templates/index.html': (
                '{% extends "base.html" %}\n'
                '{% block title %}{{ headline.title }}{% endblock %}\n'
                '{% block content %}\n'
                '<section class="container">\n'
                '<h1>{{ headline.title }}</h1>\n'
                '<p>{{ headline.subtitle }}</p>\n'
                '{% for box in boxes %}<div class="box">'
                '<h3>{{ box.title }}</h3><p>{{ box.description }}</p></div>{% endfor %}\n'
                '</section>\n'
                '{% endblock %}\n'
            ),
        })
        out = self.root / 'out-custom'
        index = (out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<h1>Custom Hero</h1>', index)
        self.assertIn('Sub here.', index)
        self.assertIn('BoxA', index)
        self.assertIn('Alpha content', index)
        self.assertIn('BoxB', index)
        self.assertIn('Beta content', index)

    def test_missing_content_files_do_not_crash(self):
        """Referencing a missing file skips the section instead of failing."""
        index = self._build('missing', {'content_files': ['index.md', 'nonexistent.md']}, {
            'content/en/index.md': '# Still Here\n\nBody.\n',
        })
        self.assertIn('Still Here', index)


if __name__ == '__main__':
    unittest.main()