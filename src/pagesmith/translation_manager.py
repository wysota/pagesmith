#!/usr/bin/env python3
"""
Translation Manager for multi-language website.
Handles loading, caching, and fallback of translation files.
"""

from pathlib import Path
import logging
import yaml


logger = logging.getLogger(__name__)


class TranslationManager:
    """
    Manages translation files and caching with fallback support.
    
    Features:
    - Loads translation YAML files with language fallback
    - Caches translations in memory for performance
    - Tracks cache statistics (hits/misses)
    - Validates language codes
    - Provides nested key access helpers
    """
    
    def __init__(self, translations_dir, default_lang):
        """
        Initialize the TranslationManager.
        
        Args:
            translations_dir (Path): Path to the translations directory
            default_lang (str): Default language code (fallback)
        """
        self.translations_dir = Path(translations_dir)
        self.default_lang = default_lang
        self.cache = {}
        self.stats = {'hits': 0, 'misses': 0, 'loads': 0}
    
    def load(self, lang):
        """
        Load translations for a language with fallback support.
        
        Returns cached translation dict if available (cache hit).
        On cache miss: loads from YAML file, falls back to default language
        if not found, creates empty dict as last resort.
        
        Args:
            lang (str): Language code (e.g., 'en', 'pl')
            
        Returns:
            dict: Translation data as loaded from YAML
        """
        # Check cache first
        if lang in self.cache:
            self.stats['hits'] += 1
            return self.cache[lang]
        
        self.stats['misses'] += 1
        
        # Try to load language-specific file
        trans_file = self.translations_dir / f'{lang}.yaml'
        if trans_file.exists():
            translations = self._load_yaml(trans_file)
            self.cache[lang] = translations
            self.stats['loads'] += 1
            return translations
        
        # Fallback to default language
        if lang != self.default_lang:
            default_file = self.translations_dir / f'{self.default_lang}.yaml'
            if default_file.exists():
                translations = self._load_yaml(default_file)
                self.cache[lang] = translations
                self.stats['loads'] += 1
                return translations
        
        # Last resort: empty dict
        self.cache[lang] = {}
        self.stats['loads'] += 1
        return {}
    
    def get_nested(self, lang, key_path, default=None):
        """
        Get a nested translation value using dot notation.
        
        Examples:
            manager.get_nested('en', 'nav.home')  # -> value of t['nav']['home']
            manager.get_nested('en', 'ui.button.submit', 'Submit')
            
        Args:
            lang (str): Language code
            key_path (str): Dot-separated path (e.g., 'nav.home')
            default: Default value if key not found
            
        Returns:
            Translation value or default
        """
        translations = self.load(lang)
        keys = key_path.split('.')
        
        current = translations
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        
        return current
    
    def is_language_valid(self, lang, valid_languages):
        """
        Validate that a language code exists in the valid languages set.
        
        Args:
            lang (str): Language code to validate
            valid_languages (dict or list): Available languages (dict keys or list items)
            
        Returns:
            bool: True if language is valid, False otherwise
        """
        if isinstance(valid_languages, dict):
            return lang in valid_languages
        return lang in valid_languages
    
    def clear_cache(self):
        """
        Clear all cached translations but keep statistics.
        Useful for rebuilds when translation files may have changed.
        """
        self.cache.clear()
    
    def reset(self):
        """
        Clear cache and reset all statistics.
        Useful for fresh starts or testing.
        """
        self.cache.clear()
        self.stats = {'hits': 0, 'misses': 0, 'loads': 0}
    
    def get_stats(self):
        """
        Get cache statistics.
        
        Returns:
            dict: Statistics with keys 'hits', 'misses', 'loads'
                  Can compute hit_rate as hits/(hits+misses) if misses > 0
        """
        return dict(self.stats)
    
    def get_hit_rate(self):
        """
        Calculate cache hit rate as a percentage.
        
        Returns:
            float: Hit rate (0-100), or 0 if no accesses yet
        """
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return (self.stats['hits'] / total) * 100
    
    def _load_yaml(self, filepath):
        """
        Safely load a YAML file.
        
        Args:
            filepath (Path): Path to YAML file
            
        Returns:
            dict: Parsed YAML content, or empty dict on error
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content if isinstance(content, dict) else {}
        except Exception as e:
            logger.warning("Error loading translation file %s: %s", filepath, e)
            return {}
