"""Built-in shortcodes module with auto-discovery and registration.

This module provides shortcodes and utilities for automatic registration.

Simple shortcodes are functions with a `name` attribute. Complex shortcodes that need
builder context are callable classes with a `name` class attribute and a set_context() method.

Usage:
    from pagesmith.shortcodes import register_shortcodes
    
    # Auto-register all shortcodes with minimum setup
    register_shortcodes(shortcode_processor, builder)
    
    # Or manually instantiate and register:
    from pagesmith.shortcodes import youtube, figure, Download
    
    processor.register('youtube', youtube)
    processor.register('figure', figure)
    
    dl = Download()
    dl.set_context(files_dir, get_urls_fn, shortcode_ctx)
    processor.register('download', dl)
"""

from .youtube import youtube
from .figure import figure
from .highlight import highlight
from .gist import gist
from .emoji import emoji
from .compiler_explorer import compiler_explorer
from .data import Data
from .download import Download
from .child_link import ChildLink
from .children import Children

__all__ = [
    'youtube',
    'figure',
    'highlight',
    'gist',
    'emoji',
    'compiler_explorer',
    'Data',
    'Download',
    'ChildLink',
    'Children',
    'get_all_shortcodes',
    'register_shortcodes',
]


def get_all_shortcodes():
    """Discover and instantiate all shortcode handlers.
    
    Returns:
        dict: {shortcode_name: handler, ...}
        
        Handlers can be:
        - Functions with a `name` attribute
        - Instances of callable classes with a `name` class attribute
    """
    shortcodes = {}
    
    # Simple function-based shortcodes
    for func in [youtube, figure, highlight, gist, emoji, compiler_explorer]:
        shortcodes[func.name] = func
    
    # Callable class-based shortcodes
    for cls in [Data, Download, ChildLink, Children]:
        instance = cls()
        shortcodes[instance.name] = instance
    
    return shortcodes


def register_shortcodes(shortcode_processor, builder):
    """Register all shortcodes with a ShortcodeProcessor.
    
    This is the recommended way to register shortcodes. It automatically
    instantiates all shortcode handlers, sets their context where needed,
    and registers them with the processor.
    
    Args:
        shortcode_processor: ShortcodeProcessor instance
        builder: SiteBuilder instance with methods like get_urls(), load_data(), etc.
    
    Example:
        from pagesmith.plugins.shortcodes import ShortcodeProcessor
        from pagesmith.shortcodes import register_shortcodes
        
        processor = ShortcodeProcessor()
        register_shortcodes(processor, site_builder)
    """
    shortcodes = get_all_shortcodes()
    
    # Register each shortcode, setting context where needed
    for name, handler in shortcodes.items():
        # Set context for shortcodes that need builder access
        if isinstance(handler, Data):
            handler.set_context(builder.load_data)
        elif isinstance(handler, Download):
            handler.set_context(
                builder.files_dir,
                builder.get_urls,
                builder._shortcode_ctx
            )
        elif isinstance(handler, ChildLink):
            handler.set_context(
                builder.sections_dir,
                builder.read_file,
                builder.parse_metadata,
                builder._shortcode_ctx
            )
        elif isinstance(handler, Children):
            handler.set_context(
                builder.sections_dir,
                builder.read_file,
                builder.parse_metadata,
                builder.template_renderer.render,
                builder._shortcode_ctx
            )
        
        # Register with processor
        shortcode_processor.register(name, handler)
