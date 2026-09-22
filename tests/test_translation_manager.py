#!/usr/bin/env python3
"""
Unit tests for TranslationManager class.
Tests loading, caching, fallback, validation, and nested access.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import yaml

from pagesmith.translation_manager import TranslationManager


class TestTranslationManager(unittest.TestCase):
    """Test cases for TranslationManager."""
    
    def setUp(self):
        """Create a temporary directory with test translation files."""
        self.temp_dir = tempfile.mkdtemp()
        self.translations_dir = Path(self.temp_dir) / 'translations'
        self.translations_dir.mkdir()
        
        # Create English (default) translation file
        self.en_data = {
            'nav': {
                'home': 'Home',
                'about': 'About',
            },
            'ui': {
                'button': {
                    'submit': 'Submit',
                    'cancel': 'Cancel',
                }
            }
        }
        with open(self.translations_dir / 'en.yaml', 'w') as f:
            yaml.dump(self.en_data, f)
        
        # Create Polish translation file (partial)
        self.pl_data = {
            'nav': {
                'home': 'Strona główna',
                'about': 'O nas',
            },
            'ui': {
                'button': {
                    'submit': 'Wyślij',
                }
            }
        }
        with open(self.translations_dir / 'pl.yaml', 'w') as f:
            yaml.dump(self.pl_data, f)
        
        # Create manager with English as default
        self.manager = TranslationManager(self.translations_dir, 'en')
    
    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_existing_language(self):
        """Test loading an existing translation file."""
        trans = self.manager.load('en')
        self.assertEqual(trans['nav']['home'], 'Home')
        self.assertEqual(trans['ui']['button']['submit'], 'Submit')
    
    def test_load_uses_cache(self):
        """Test that second load uses cache (cache hit)."""
        # First load - miss
        self.manager.load('en')
        self.assertEqual(self.manager.stats['misses'], 1)
        self.assertEqual(self.manager.stats['hits'], 0)
        
        # Second load - hit
        self.manager.load('en')
        self.assertEqual(self.manager.stats['misses'], 1)
        self.assertEqual(self.manager.stats['hits'], 1)
    
    def test_load_fallback_to_default(self):
        """Test fallback to default language when translation missing."""
        # Load German (doesn't exist) - should fallback to English
        trans = self.manager.load('de')
        self.assertEqual(trans['nav']['home'], 'Home')
        self.assertIn('de', self.manager.cache)
    
    def test_load_nonexistent_language_no_fallback(self):
        """Test behavior when language and default language don't exist."""
        # Create new manager with non-existent default
        manager = TranslationManager(self.translations_dir, 'xx')
        trans = manager.load('yy')
        self.assertEqual(trans, {})
    
    def test_different_languages_separate_caches(self):
        """Test that different languages are cached separately."""
        en_trans = self.manager.load('en')
        pl_trans = self.manager.load('pl')
        
        self.assertNotEqual(id(en_trans), id(pl_trans))
        self.assertEqual(en_trans['nav']['home'], 'Home')
        self.assertEqual(pl_trans['nav']['home'], 'Strona główna')
    
    def test_get_nested_simple_path(self):
        """Test nested key access with simple dot path."""
        value = self.manager.get_nested('en', 'nav.home')
        self.assertEqual(value, 'Home')
    
    def test_get_nested_deep_path(self):
        """Test nested key access with deep dot path."""
        value = self.manager.get_nested('en', 'ui.button.submit')
        self.assertEqual(value, 'Submit')
    
    def test_get_nested_missing_key(self):
        """Test nested access returns default for missing keys."""
        value = self.manager.get_nested('en', 'missing.key', 'DEFAULT')
        self.assertEqual(value, 'DEFAULT')
    
    def test_get_nested_partial_path(self):
        """Test nested access with missing intermediate keys."""
        value = self.manager.get_nested('en', 'nav.missing.key', 'DEFAULT')
        self.assertEqual(value, 'DEFAULT')
    
    def test_get_nested_with_fallback_lang(self):
        """Test nested access works with fallback language."""
        # Load German (falls back to English)
        value = self.manager.get_nested('de', 'nav.home')
        self.assertEqual(value, 'Home')
    
    def test_is_language_valid_dict(self):
        """Test language validation with dict of languages."""
        valid_langs = {'en': {}, 'pl': {}}
        self.assertTrue(self.manager.is_language_valid('en', valid_langs))
        self.assertTrue(self.manager.is_language_valid('pl', valid_langs))
        self.assertFalse(self.manager.is_language_valid('de', valid_langs))
    
    def test_is_language_valid_list(self):
        """Test language validation with list of languages."""
        valid_langs = ['en', 'pl', 'de']
        self.assertTrue(self.manager.is_language_valid('en', valid_langs))
        self.assertFalse(self.manager.is_language_valid('fr', valid_langs))
    
    def test_clear_cache(self):
        """Test clearing cache."""
        # Load both languages
        self.manager.load('en')
        self.manager.load('pl')
        self.assertEqual(len(self.manager.cache), 2)
        
        # Clear cache
        self.manager.clear_cache()
        self.assertEqual(len(self.manager.cache), 0)
        
        # Stats should still exist
        self.assertEqual(self.manager.stats['loads'], 2)
    
    def test_reset_clears_cache_and_stats(self):
        """Test reset clears both cache and statistics."""
        self.manager.load('en')
        self.manager.load('pl')
        
        self.assertEqual(len(self.manager.cache), 2)
        self.assertGreater(self.manager.stats['loads'], 0)
        
        self.manager.reset()
        
        self.assertEqual(len(self.manager.cache), 0)
        self.assertEqual(self.manager.stats['hits'], 0)
        self.assertEqual(self.manager.stats['misses'], 0)
        self.assertEqual(self.manager.stats['loads'], 0)
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        self.manager.load('en')  # miss, load
        self.manager.load('en')  # hit
        self.manager.load('pl')  # miss, load
        self.manager.load('pl')  # hit
        
        stats = self.manager.get_stats()
        self.assertEqual(stats['hits'], 2)
        self.assertEqual(stats['misses'], 2)
        self.assertEqual(stats['loads'], 2)
    
    def test_get_hit_rate(self):
        """Test cache hit rate calculation."""
        # All misses
        self.manager.load('en')
        self.manager.load('pl')
        self.assertEqual(self.manager.get_hit_rate(), 0.0)
        
        # Reset and do mixed
        self.manager.reset()
        self.manager.load('en')  # miss
        self.manager.load('en')  # hit
        hit_rate = self.manager.get_hit_rate()
        self.assertEqual(hit_rate, 50.0)
    
    def test_get_hit_rate_no_accesses(self):
        """Test hit rate returns 0 when no accesses."""
        manager = TranslationManager(self.translations_dir, 'en')
        self.assertEqual(manager.get_hit_rate(), 0.0)
    
    def test_load_yaml_error_handling(self):
        """Test graceful handling of YAML parse errors."""
        # Create a file with invalid YAML
        bad_file = self.translations_dir / 'bad.yaml'
        bad_file.write_text('{ invalid yaml: [')
        
        manager = TranslationManager(self.translations_dir, 'en')
        # Should not crash, should return empty dict
        trans = manager._load_yaml(bad_file)
        self.assertEqual(trans, {})
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        nonexistent = self.translations_dir / 'nonexistent.yaml'
        trans = self.manager._load_yaml(nonexistent)
        self.assertEqual(trans, {})


class TestTranslationManagerIntegration(unittest.TestCase):
    """Integration tests with realistic scenarios."""
    
    def setUp(self):
        """Create a more realistic translation setup."""
        self.temp_dir = tempfile.mkdtemp()
        self.translations_dir = Path(self.temp_dir) / 'translations'
        self.translations_dir.mkdir()
        
        # English (complete)
        en = {
            'nav': {'home': 'Home', 'about': 'About', 'services': 'Services'},
            'ui': {'get_started': 'Get Started', 'contact': 'Contact Us'},
            'errors': {'not_found': '404 - Page not found'},
        }
        yaml.dump(en, open(self.translations_dir / 'en.yaml', 'w'))
        
        # Polish (partial - missing 'errors' section)
        pl = {
            'nav': {'home': 'Strona główna', 'about': 'O nas', 'services': 'Usługi'},
            'ui': {'get_started': 'Zacznij', 'contact': 'Skontaktuj się'},
        }
        yaml.dump(pl, open(self.translations_dir / 'pl.yaml', 'w'))
        
        self.manager = TranslationManager(self.translations_dir, 'en')
    
    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_realistic_workflow(self):
        """Test a realistic workflow: load multiple languages, access values."""
        # Load English
        en = self.manager.load('en')
        self.assertEqual(self.manager.stats['loads'], 1)
        self.assertEqual(self.manager.stats['misses'], 1)
        
        # Get a nested value (uses cache, causes hit)
        home_text = self.manager.get_nested('en', 'nav.home')
        self.assertEqual(home_text, 'Home')
        self.assertEqual(self.manager.stats['hits'], 1)  # get_nested calls load()
        
        # Load Polish (new language, causes miss)
        pl = self.manager.load('pl')
        self.assertEqual(self.manager.stats['loads'], 2)
        self.assertEqual(self.manager.stats['misses'], 2)
        
        # Get nested value from Polish (uses cache, causes hit)
        home_pl = self.manager.get_nested('pl', 'nav.home')
        self.assertEqual(home_pl, 'Strona główna')
        self.assertEqual(self.manager.stats['hits'], 2)  # Another cache hit from get_nested
        
        # Access English again (should be cache hit)
        en2 = self.manager.load('en')
        self.assertEqual(self.manager.stats['hits'], 3)  # Another hit
        self.assertIs(en, en2)  # Same object from cache
    
    def test_cache_hit_rate_realistic(self):
        """Test hit rate in realistic scenario with 3 languages."""
        # Simulate template rendering accessing translations repeatedly
        for _ in range(10):
            self.manager.load('en')
            self.manager.load('pl')
        
        # Expected: 2 misses (first load), 18 hits (subsequent loads)
        stats = self.manager.get_stats()
        self.assertEqual(stats['misses'], 2)
        self.assertEqual(stats['hits'], 18)
        
        hit_rate = self.manager.get_hit_rate()
        expected_rate = (18 / 20) * 100
        self.assertAlmostEqual(hit_rate, expected_rate)


if __name__ == '__main__':
    unittest.main()
