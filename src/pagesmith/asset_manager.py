"""
Asset management module for file I/O, asset copying, and data loading.
Handles reading markdown files, loading YAML data, copying images/assets/files.
"""

import re
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, Any

import yaml


logger = logging.getLogger(__name__)


class AssetManager:
    """
    Manages all file I/O operations including reading content, loading data, and copying assets.
    Provides language-aware file loading with fallback to default language.
    """
    
    def __init__(
        self,
        content_dir: Path,
        sections_dir: Path,
        data_dir: Path,
        images_dir: Path,
        assets_dir: Path,
        files_dir: Path,
        output_dir: Path,
        default_lang: str,
    ):
        """
        Initialize AssetManager.
        
        Args:
            content_dir: Path to content directory (home page sections)
            sections_dir: Path to sections directory (pages)
            data_dir: Path to data directory (YAML data files)
            images_dir: Path to images directory
            assets_dir: Path to assets directory (CSS, JS, etc.)
            files_dir: Path to downloadable files directory
            output_dir: Path to output/build directory
            default_lang: Default language code for fallback
        """
        self.content_dir = content_dir
        self.sections_dir = sections_dir
        self.data_dir = data_dir
        self.images_dir = images_dir
        self.assets_dir = assets_dir
        self.files_dir = files_dir
        self.output_dir = output_dir
        self.default_lang = default_lang
        
        # Cache for data
        self.data_cache: Optional[Dict[str, Any]] = None
    
    def read_file(self, filepath: Path) -> str:
        """
        Read a file safely with fallback.
        
        Args:
            filepath: Path to file to read
            
        Returns:
            File contents as string, empty string if file not found
        """
        if not filepath.exists():
            logger.warning("%s not found", filepath)
            return ""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def load_content_file(self, filename: str, lang: str) -> str:
        """
        Load content file with fallback to default language.
        Used for home page sections like hero.md, services.md, about.md.
        
        Args:
            filename: Name of content file (e.g., 'hero.md')
            lang: Language code
            
        Returns:
            File contents with language fallback
        """
        lang_path = self.content_dir / lang / filename
        if lang_path.exists():
            return self.read_file(lang_path)
        
        # Fallback to default language
        default_path = self.content_dir / self.default_lang / filename
        return self.read_file(default_path)
    
    def load_section_file(self, filename: str, lang: str) -> str:
        """
        Load section markdown file with fallback to default language.
        Used for page sections and child pages.
        
        Args:
            filename: Name or path of section file (e.g., 'contact.md' or 'parent/child.md')
            lang: Language code
            
        Returns:
            File contents with language fallback
        """
        lang_path = self.sections_dir / lang / filename
        if lang_path.exists():
            return self.read_file(lang_path)
        
        # Fallback to default language
        default_path = self.sections_dir / self.default_lang / filename
        return self.read_file(default_path)
    
    def load_data(self) -> Dict[str, Any]:
        """
        Load all YAML data files from the data directory.
        Results are cached in memory for performance.
        
        Returns:
            Dict mapping data file names (stems) to parsed YAML content
        """
        if self.data_cache is not None:
            return self.data_cache
        
        self.data_cache = {}
        
        if not self.data_dir.exists():
            return self.data_cache
        
        # Read all .yaml and .yml files
        data_files = list(self.data_dir.glob('*.yaml')) + list(self.data_dir.glob('*.yml'))
        for data_file in data_files:
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    key = data_file.stem
                    self.data_cache[key] = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning("Error loading data file %s: %s", data_file, e)
        
        return self.data_cache
    
    def clear_data_cache(self) -> None:
        """Clear the data cache (useful before rebuild)."""
        self.data_cache = None
    
    def _safe_rmtree(self, rel_subdir: str) -> None:
        """
        Remove a subdirectory of output_dir, refusing paths outside output_dir.
        
        Guards destructive deletes against a misconfigured output_dir so a
        typo can never cause a recursive delete of source/user data.
        
        Args:
            rel_subdir: Subdirectory name relative to output_dir (e.g., 'images')
            
        Raises:
            ValueError: If the resolved target escapes output_dir
        """
        target = self.output_dir / rel_subdir
        if not target.exists():
            return
        if self.output_dir.resolve() not in target.resolve().parents:
            raise ValueError(
                f"Refusing to delete {target}: outside output_dir {self.output_dir}"
            )
        shutil.rmtree(target)
    
    def copy_images(self) -> None:
        """Copy images directory to output."""
        if self.images_dir.exists():
            output_images = self.output_dir / 'images'
            self._safe_rmtree('images')
            shutil.copytree(self.images_dir, output_images)
            logger.debug("Copied images")
    
    def minify_css(self, css_content: str) -> str:
        """
        Basic CSS minification: remove comments, extra whitespace, and empty lines.
        
        Args:
            css_content: Raw CSS content
            
        Returns:
            Minified CSS
        """
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove multiple spaces
        css_content = re.sub(r'\s+', ' ', css_content)
        
        # Remove spaces around special characters
        css_content = re.sub(r'\s*([{};:,>+~])\s*', r'\1', css_content)
        
        # Remove trailing semicolons before closing braces
        css_content = re.sub(r';}', '}', css_content)
        
        # Remove leading/trailing whitespace
        css_content = css_content.strip()
        
        return css_content
    
    def copy_assets(self) -> None:
        """Copy assets directory to output with optional CSS minification."""
        if not self.assets_dir.exists():
            return
        
        output_assets = self.output_dir / 'assets'
        
        # Remove existing assets if present
        self._safe_rmtree('assets')
        
        # Copy assets directory
        shutil.copytree(self.assets_dir, output_assets)
        
        # Minify CSS files
        for css_file in output_assets.rglob('*.css'):
            with open(css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            minified_css = self.minify_css(css_content)
            
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(minified_css)
        
        logger.debug("Copied and minified assets")
    
    def copy_files(self) -> None:
        """Copy downloadable files directory to output."""
        if self.files_dir.exists():
            output_files = self.output_dir / 'files'
            self._safe_rmtree('files')
            shutil.copytree(self.files_dir, output_files)
            logger.debug("Copied downloadable files")
