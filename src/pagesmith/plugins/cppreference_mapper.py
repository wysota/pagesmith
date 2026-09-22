"""
CPPReference XML mapper for automatic C++ standard library documentation linking.

This module downloads and caches cppreference XML index files from:
- https://raw.githubusercontent.com/p12tic/cppreference-doc/master/index-functions-c.xml
- https://raw.githubusercontent.com/p12tic/cppreference-doc/master/index-functions-cpp.xml

It parses these to build lookup tables for C and C++ standard library symbols,
enabling automatic linking in code documentation.
"""

import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError


logger = logging.getLogger(__name__)


class CPPReferenceMapper:
    """Maps C/C++ standard library symbols to cppreference.com URLs."""

    # Official cppreference XML sources
    CPPREFERENCE_SOURCES = {
        'C': 'https://raw.githubusercontent.com/p12tic/cppreference-doc/master/index-functions-c.xml',
        'C++': 'https://raw.githubusercontent.com/p12tic/cppreference-doc/master/index-functions-cpp.xml',
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the cppreference mapper.

        Args:
            cache_dir: Directory to cache XML files. Defaults to ~/.cache/cppreference/
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.cache' / 'cppreference'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Lookup tables: {lang: {symbol: url}}
        self.c_symbols: Dict[str, str] = {}
        self.cpp_symbols: Dict[str, str] = {}
        self.loaded = False

    def load(self, force_refresh: bool = False) -> bool:
        """
        Load cppreference data from cache or download if needed.

        Args:
            force_refresh: If True, download fresh copies even if cached

        Returns:
            True if loaded successfully, False otherwise
        """
        if self.loaded and not force_refresh:
            return True

        try:
            self._load_language_data('C', self.c_symbols, force_refresh)
            self._load_language_data('C++', self.cpp_symbols, force_refresh)
            self.loaded = True
            logger.debug("CPPReference loaded %s C symbols, %s C++ symbols", len(self.c_symbols), len(self.cpp_symbols))
            return True
        except Exception as e:
            logger.warning("Failed to load symbols: %s", e)
            return False

    def _load_language_data(self, lang: str, symbols_dict: Dict[str, str], force_refresh: bool):
        """Load symbols for a specific language."""
        cache_path = self.cache_dir / f"index-functions-{lang.lower()}.xml"
        
        # Download if not cached or force_refresh
        if force_refresh or not cache_path.exists():
            self._download_xml(lang, cache_path)
        
        # Parse cached XML
        if cache_path.exists():
            self._parse_xml(cache_path, symbols_dict)

    def _download_xml(self, lang: str, cache_path: Path):
        """Download XML file from cppreference."""
        url = self.CPPREFERENCE_SOURCES.get(lang)
        if not url:
            raise ValueError(f"Unknown language: {lang}")

        logger.debug("Downloading %s index from %s", lang, url)
        try:
            with urlopen(url, timeout=10) as response:
                data = response.read()
                cache_path.write_bytes(data)
                logger.debug("Cached %s index to %s", lang, cache_path)
        except URLError as e:
            raise RuntimeError(f"Failed to download {lang} index: {e}")

    def _parse_xml(self, xml_path: Path, symbols_dict: Dict[str, str]):
        """Parse XML index file and extract symbol URLs."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.warning("Failed to parse XML: %s", e)
            return

        # XML structure: various element types (typedef, function, class, etc.)
        # with name="symbol" link="url" attributes
        for element in root.iter():
            name = element.get('name')
            link = element.get('link')
            
            # Skip elements without both name and link
            if not name or not link:
                continue
            
            # Skip relative links like "."
            if link == '.':
                continue
            
            # Normalize to absolute URL
            if not link.startswith(('http://', 'https://')):
                # cppreference XML uses paths like "cpp/container/vector"
                # Need to add "/w/" prefix if not already there
                if not link.startswith('/w/'):
                    if link.startswith('/'):
                        link = f"/w{link}"
                    else:
                        link = f"/w/{link}"
                link = f"https://en.cppreference.com{link}"
            
            # Add to dictionary
            if name not in symbols_dict:  # Keep first occurrence
                symbols_dict[name] = link

    def lookup(self, symbol: str, lang: str = 'C++') -> Optional[str]:
        """
        Look up a symbol and return its cppreference URL.

        Args:
            symbol: C/C++ symbol name (e.g., 'std::vector', 'strlen')
            lang: 'C' or 'C++'

        Returns:
            URL or None if not found
        """
        if not self.loaded:
            return None

        symbols = self.cpp_symbols if lang == 'C++' else self.c_symbols
        return symbols.get(symbol)

    def lookup_std_symbol(self, symbol: str) -> Optional[str]:
        """
        Look up a std:: symbol in C++ standard library.

        Args:
            symbol: Full symbol like 'std::vector', 'std::string', etc.

        Returns:
            URL or None if not found
        """
        if not self.loaded:
            return None

        # Try exact match first
        if symbol in self.cpp_symbols:
            return self.cpp_symbols[symbol]

        # Try partial match (for overloads, etc.)
        # e.g., 'std::vector::push_back' -> 'std::vector'
        parts = symbol.split('::')
        for i in range(len(parts), 0, -1):
            partial = '::'.join(parts[:i])
            if partial in self.cpp_symbols:
                return self.cpp_symbols[partial]

        return None

    def lookup_c_symbol(self, symbol: str) -> Optional[str]:
        """
        Look up a C standard library symbol.

        Args:
            symbol: C symbol like 'strlen', 'printf', etc.

        Returns:
            URL or None if not found
        """
        if not self.loaded:
            return None

        return self.c_symbols.get(symbol)


def get_mapper(cache_dir: Optional[Path] = None) -> CPPReferenceMapper:
    """Get or create a global CPPReferenceMapper instance."""
    if not hasattr(get_mapper, '_instance'):
        get_mapper._instance = CPPReferenceMapper(cache_dir)
    return get_mapper._instance
