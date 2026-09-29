"""Tests for the add-site scaffold."""

import tempfile
import unittest
from pathlib import Path

from pagesmith import paths
from pagesmith.builder import SiteBuilder
from pagesmith.manager import create_site


class TestCreateSite(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.site = create_site('demo', title='Demo Site', base_dir=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scaffold_layout(self):
        self.assertTrue((self.site / 'config' / 'site.yaml').is_file())
        for rel in [
            'content/en/index.md',
            'translations/en.yaml',
            'assets/css/style.css',
            'assets/favicon.svg',
        ]:
            self.assertTrue((self.site / rel).is_file(), rel)
        # The minimal scaffold ships no sections, nav data, or extra content.
        for rel in [
            'content/en/hero.md',
            'content/en/services.md',
            'content/en/about.md',
            'content/en/skills.md',
            'sections/en/services.md',
            'sections/en/about.md',
            'sections/en/contact.md',
            'data/nav.yaml',
            'config/link_schemes.yaml',
            'assets/js/main.js',
        ]:
            self.assertFalse((self.site / rel).exists(), rel)

    def test_scaffold_config_is_minimal(self):
        config = paths.load_site_config(self.site)
        self.assertNotIn('output_dir', config['build'])
        # Only the index page is configured.
        self.assertEqual(list(config['pages']), ['index'])
        # Taxonomies are disabled so no extra pages are generated.
        self.assertFalse(config['taxonomies']['tags']['enabled'])
        self.assertFalse(config['taxonomies']['categories']['enabled'])
        # A single Markdown file composes the index page.
        self.assertEqual(config['pages']['index']['content_files'], ['index.md'])

    def test_scaffolded_site_builds_and_is_self_contained(self):
        out = self.root / 'out'
        builder = SiteBuilder(self.site, str(out))
        self.assertTrue(builder.build())

        index = (out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Demo Site', index)
        # No references to the development default site.
        for marker in ('wysota', 'linkedin.com', 'github.com/wysota'):
            self.assertNotIn(marker, index)

        # Only the index page and assets are generated.
        for rel in ['assets/css/style.css', 'assets/favicon.svg']:
            self.assertTrue((out / rel).is_file(), rel)
        self.assertFalse((out / 'sections').exists(), 'no section pages expected')
        self.assertFalse((out / 'tags').exists(), 'no taxonomy pages expected')


if __name__ == '__main__':
    unittest.main()
