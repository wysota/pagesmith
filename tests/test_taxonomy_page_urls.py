"""Regression tests for links from taxonomy term pages back to section pages.

A term page lives at ``tags/{term}/index.html`` (two levels below the language
root) in every language, so the URLs it exposes for tagged section pages must
be ``../../sections/...`` and must never contain a double slash.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from pagesmith.builder import SiteBuilder


GUIDE = """---
title: Guide
tags: [alpha]
---

# Guide
"""

CHILD = """---
title: Child
tags: [alpha]
---

# Child
"""


def _make_site(root, name, languages):
    site = root / name
    (site / 'config').mkdir(parents=True)
    (site / 'translations').mkdir(parents=True)
    (site / 'assets' / 'css').mkdir(parents=True)

    config = {
        'site': {'name': name.title(), 'base_url': f'https://{name}.example.com'},
        'languages': languages,
        'taxonomies': {
            'tags': {'singular': 'tag', 'plural': 'tags', 'slug': 'tags', 'enabled': True},
            'categories': {
                'singular': 'category', 'plural': 'categories',
                'slug': 'categories', 'enabled': False,
            },
        },
        'pages': {
            'index': {'template': 'index.html', 'content_files': ['index.md']},
            'guide': {
                'template': 'page.html', 'nav_name': 'GUIDE',
                'markdown': 'guide.md', 'section': True,
            },
        },
    }
    (site / 'config' / 'site.yaml').write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding='utf-8',
    )

    (site / 'assets' / 'css' / 'style.css').write_text('body {}\n', encoding='utf-8')
    (site / 'assets' / 'favicon.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding='utf-8')
    for code in languages:
        (site / 'translations' / f'{code}.yaml').write_text(
            'footer:\n  copyright: All rights reserved.\n', encoding='utf-8')

    files = {
        'content/en/index.md': '# Site\n\nHome.\n',
        'sections/en/guide.md': GUIDE,
        'sections/en/guide/child.md': CHILD,
    }
    if 'pl' in languages:
        files.update({
            'content/pl/index.md': '# Strona\n\nStart.\n',
            'sections/pl/guide.md': GUIDE,
            'sections/pl/guide/child.md': CHILD,
        })
    for rel, content in files.items():
        path = site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    return site


class TestTaxonomyPageUrls(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, languages):
        site = _make_site(self.root, 'tax', languages)
        out = self.root / 'out'
        builder = SiteBuilder(site, str(out))
        self.assertTrue(builder.build(), 'build failed')
        return out

    def _term_page(self, out, lang):
        term = out / 'tags' / 'alpha' / 'index.html'
        if lang != 'en':
            term = out / lang / 'tags' / 'alpha' / 'index.html'
        self.assertTrue(term.exists(), f'term page missing: {term}')
        return term.read_text(encoding='utf-8')

    def test_default_language_term_page_links(self):
        out = self._build({'en': {'name': 'English', 'code': 'en', 'default': True}})
        html = self._term_page(out, 'en')
        self.assertIn('href="../../sections/guide.html"', html)
        self.assertIn('href="../../sections/guide/child.html"', html)
        self.assertNotIn('//sections', html)

    def test_non_default_language_term_page_links(self):
        languages = {
            'en': {'name': 'English', 'code': 'en', 'default': True},
            'pl': {'name': 'Polski', 'code': 'pl', 'default': False},
        }
        out = self._build(languages)
        for lang in ('en', 'pl'):
            html = self._term_page(out, lang)
            self.assertIn('href="../../sections/guide.html"', html,
                          f'{lang}: top-level page URL wrong')
            self.assertIn('href="../../sections/guide/child.html"', html,
                          f'{lang}: child page URL wrong')
            self.assertNotIn('//sections', html, f'{lang}: double slash in URL')


if __name__ == '__main__':
    unittest.main()
