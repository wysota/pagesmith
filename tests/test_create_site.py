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
            'content/en/hero.md',
            'content/en/services.md',
            'content/en/about.md',
            'content/en/skills.md',
            'sections/en/services.md',
            'sections/en/about.md',
            'sections/en/contact.md',
            'translations/en.yaml',
            'assets/css/style.css',
            'assets/js/main.js',
            'assets/favicon.svg',
        ]:
            self.assertTrue((self.site / rel).is_file(), rel)

    def test_scaffold_config_has_no_output_dir(self):
        config = paths.load_site_config(self.site)
        self.assertNotIn('output_dir', config['build'])

    def test_scaffolded_site_builds_and_is_self_contained(self):
        out = self.root / 'out'
        builder = SiteBuilder(self.site, str(out))
        self.assertTrue(builder.build())

        index = (out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Demo Site', index)
        # No references to the development default site.
        for marker in ('wysota', 'linkedin.com', 'github.com/wysota'):
            self.assertNotIn(marker, index)

        for rel in ['assets/css/style.css', 'sections/about.html',
                    'sections/contact.html', 'sections/services.html']:
            self.assertTrue((out / rel).is_file(), rel)


if __name__ == '__main__':
    unittest.main()
