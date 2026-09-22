"""Tests for site.yaml loading, validation, and defaulting."""

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from pagesmith import cli, paths
from pagesmith.builder import SiteBuilder
from pagesmith.manager import create_site
from pagesmith.paths import ConfigError


def _write_config(site, text):
    config = site / 'config' / 'site.yaml'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(text, encoding='utf-8')
    return config


class TestLoadSiteConfig(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name).resolve() / 'mysite'
        (self.site / 'config').mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_defaults_applied_when_section_missing(self):
        _write_config(self.site,
                      'languages:\n  en:\n    name: English\n'
                      'pages:\n  index:\n    template: index.html\n')
        config = paths.load_site_config(self.site)
        self.assertEqual(config['build'], paths.DEFAULT_BUILD)
        self.assertEqual(config['build']['content_dir'], 'content')

    def test_build_partial_section_merged_with_defaults(self):
        _write_config(self.site,
                      'languages:\n  en:\n    name: English\n'
                      'build:\n  content_dir: src\n  posts_per_page: 2\n'
                      'pages:\n  index:\n    template: index.html\n')
        build = paths.load_site_config(self.site)['build']
        self.assertEqual(build['content_dir'], 'src')
        self.assertEqual(build['posts_per_page'], 2)
        self.assertEqual(build['sections_dir'], 'sections')

    def test_taxonomies_defaulted_when_omitted(self):
        _write_config(self.site,
                      'languages:\n  en:\n    name: English\n'
                      'pages:\n  index:\n    template: index.html\n')
        config = paths.load_site_config(self.site)
        self.assertIn('tags', config['taxonomies'])
        self.assertIn('categories', config['taxonomies'])

    def test_default_language_flagged_when_none_set(self):
        _write_config(self.site,
                      'languages:\n  pl:\n    name: Polski\n  en:\n    name: English\n'
                      'pages:\n  index:\n    template: index.html\n')
        languages = paths.load_site_config(self.site)['languages']
        self.assertTrue(languages['pl']['default'])
        self.assertFalse(languages['en']['default'])

    def test_site_name_defaults_to_directory_name(self):
        _write_config(self.site,
                      'languages:\n  en:\n    name: English\n'
                      'pages:\n  index:\n    template: index.html\n')
        self.assertEqual(paths.load_site_config(self.site)['site']['name'], 'mysite')

    def test_missing_languages_raises_config_error(self):
        _write_config(self.site, 'site:\n  name: X\n')
        with self.assertRaises(ConfigError):
            paths.load_site_config(self.site)

    def test_missing_pages_raises_config_error(self):
        _write_config(self.site, 'languages:\n  en:\n    name: English\n')
        with self.assertRaises(ConfigError):
            paths.load_site_config(self.site)

    def test_pages_without_index_raises_config_error(self):
        _write_config(self.site,
                      'languages:\n  en:\n    name: English\n'
                      'pages:\n  about:\n    template: page.html\n')
        with self.assertRaises(ConfigError):
            paths.load_site_config(self.site)

    def test_invalid_yaml_raises_config_error(self):
        _write_config(self.site, 'site: [unclosed\n')
        with self.assertRaises(ConfigError):
            paths.load_site_config(self.site)

    def test_non_mapping_config_raises_config_error(self):
        _write_config(self.site, '- just\n- a\n- list\n')
        with self.assertRaises(ConfigError):
            paths.load_site_config(self.site)

    def test_config_error_is_value_error(self):
        self.assertTrue(issubclass(ConfigError, ValueError))


class TestMinimalSiteBuilds(unittest.TestCase):
    """A site whose config omits ``build`` still builds using defaults."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.site = create_site('minimal', title='Minimal', base_dir=self.root)
        config_path = self.site / 'config' / 'site.yaml'
        lines = config_path.read_text(encoding='utf-8').splitlines()
        # Drop the whole top-level build: block.
        kept, skipping = [], False
        for line in lines:
            if line.startswith('build:'):
                skipping = True
                continue
            if skipping and line and not line[0].isspace():
                skipping = False
            if not skipping:
                kept.append(line)
        config_path.write_text('\n'.join(kept) + '\n', encoding='utf-8')
        self.assertNotIn('build:', config_path.read_text(encoding='utf-8'))

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_succeeds_with_defaults(self):
        out = self.root / 'out'
        builder = SiteBuilder(self.site, str(out))
        self.assertTrue(builder.build())
        self.assertTrue((out / 'index.html').is_file())


class TestCliSiteArgument(unittest.TestCase):

    def test_positional_site_parsed(self):
        args = cli.build_parser().parse_args(['build', 'zbosk'])
        self.assertEqual(args.site_name, 'zbosk')

    def test_positional_site_rejected_for_add_page(self):
        # add-page has its own positional (the page name); a trailing site name
        # is not silently swallowed.
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(['add-page', 'portfolio', 'zbosk'])

    def test_conflicting_site_names_rejected(self):
        args = Namespace(site_name='a', site='b', site_dir=None)
        with self.assertRaises(ValueError):
            cli._resolve(args)


if __name__ == '__main__':
    unittest.main()
