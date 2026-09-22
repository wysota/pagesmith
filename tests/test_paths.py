"""Tests for site and output path resolution."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pagesmith import paths


def _make_site(root, name):
    site = (root / 'sites' / name).resolve()
    (site / 'config').mkdir(parents=True)
    (site / 'config' / 'site.yaml').write_text(
        'site:\n  name: Test\nbuild:\n  output_dir: html\n', encoding='utf-8')
    return site


class TestResolveSiteDir(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.site = _make_site(self.root, 'default')
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop(paths.ENV_SITE_DIR, None)

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def test_explicit_site_dir_wins(self):
        other = _make_site(self.root, 'other')
        os.environ[paths.ENV_SITE_DIR] = str(other)
        self.assertEqual(
            paths.resolve_site_dir(site_dir=str(self.site), site='other', cwd=self.root),
            self.site)

    def test_env_site_dir(self):
        os.environ[paths.ENV_SITE_DIR] = str(self.site)
        self.assertEqual(paths.resolve_site_dir(cwd=self.root), self.site)

    def test_site_name_in_cwd(self):
        self.assertEqual(
            paths.resolve_site_dir(site='default', cwd=self.root), self.site)

    def test_missing_site_raises(self):
        with self.assertRaises(FileNotFoundError):
            paths.resolve_site_dir(site='nope', cwd=self.root)

    def test_no_site_raises_systemexit(self):
        with self.assertRaises(SystemExit):
            paths.resolve_site_dir(cwd=self.root)

    def test_bad_site_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            paths.resolve_site_dir(site_dir=str(self.root / 'not-a-site'))


class TestResolveOutputDir(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.site = _make_site(self.root, 'default')
        self.config = {'build': {'output_dir': 'html'}}
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop(paths.ENV_OUTPUT, None)

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def test_cli_output_wins(self):
        target = self.root / 'explicit'
        self.assertEqual(
            paths.resolve_output_dir(self.site, output=str(target), config=self.config),
            target)

    def test_env_output(self):
        target = self.root / 'from-env'
        os.environ[paths.ENV_OUTPUT] = str(target)
        self.assertEqual(
            paths.resolve_output_dir(self.site, config=self.config), target)

    def test_config_relative_to_site(self):
        self.assertEqual(
            paths.resolve_output_dir(self.site, config=self.config, cwd=self.root),
            (self.site / 'html').resolve())

    def test_config_absolute(self):
        target = self.root / 'abs-out'
        config = {'build': {'output_dir': str(target)}}
        self.assertEqual(
            paths.resolve_output_dir(self.site, config=config, cwd=self.root),
            target.resolve())

    def test_default_is_cwd_build_name(self):
        self.assertEqual(
            paths.resolve_output_dir(self.site, config={}, cwd=self.root),
            (self.root / 'build' / 'default').resolve())

    def test_rejects_site_root(self):
        with self.assertRaises(ValueError):
            paths.resolve_output_dir(self.site, output=str(self.site))

    def test_rejects_site_ancestor(self):
        with self.assertRaises(ValueError):
            paths.resolve_output_dir(self.site, output=str(self.root))

    def test_rejects_source_subdir(self):
        with self.assertRaises(ValueError):
            paths.resolve_output_dir(self.site, output=str(self.site / 'assets'))


if __name__ == '__main__':
    unittest.main()
