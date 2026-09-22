import hashlib
import importlib.util
import logging
import sys
from pathlib import Path


logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers, loads, and manages plugins and their hooks."""

    VALID_HOOKS = [
        'before_build',
        'after_build',
        'before_render_page',
        'after_render_page',
        'before_render_post',
        'after_render_post',
        'after_content_parse',
        'plugin_markdown_extensions',
        'plugin_jinja2_extensions',
    ]

    def __init__(self, site_builder=None):
        self.site_builder = site_builder
        self.plugins = []
        self.hooks = {hook: [] for hook in self.VALID_HOOKS}
        self.shortcode_registry = None
        self.markdown_extensions = []
        self.jinja2_extensions = []

    def set_shortcode_registry(self, registry):
        """Link to the ShortcodeProcessor for shortcode registration."""
        self.shortcode_registry = registry

    def discover(self, plugins_dir):
        """Find all Python files in plugins/ directory."""
        pdir = Path(plugins_dir)
        if not pdir.exists():
            return []
        return sorted(pdir.glob('*.py'))

    def load_plugin(self, filepath):
        """Load a single plugin from a file path."""
        filepath = Path(filepath)
        # Include a directory tag so a built-in plugin and a same-named site
        # plugin don't collide in sys.modules.
        tag = hashlib.sha1(str(filepath.parent.resolve()).encode()).hexdigest()[:8]
        module_name = f'pagesmith_plugin_{filepath.stem}_{tag}'
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f'Cannot load plugin: {filepath}')

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        if hasattr(module, 'register') and callable(module.register):
            module.register(self)
            self.plugins.append(module)
            logger.debug('Plugin loaded: %s', filepath.name)
        # Files without a register() function are treated as helper modules
        # (e.g. shared mappers imported by real plugins) and silently skipped.

        return module

    SKIP_FILES = {'__init__.py', 'shortcodes.py', 'plugin_manager.py'}

    def load_all(self, plugins_dir=None):
        """Discover and load all plugins."""
        if not plugins_dir:
            return

        for plugin_file in self.discover(plugins_dir):
            if plugin_file.name in self.SKIP_FILES:
                continue
            try:
                self.load_plugin(plugin_file)
            except Exception as e:
                logger.warning('Failed to load plugin %s: %s', plugin_file.name, e)

    def register_hook(self, hook_name, callback):
        """Register a hook callback."""
        if hook_name not in self.hooks:
            raise ValueError(f'Invalid hook: {hook_name}')
        self.hooks[hook_name].append(callback)

    def run_hooks(self, hook_name, *args, **kwargs):
        """Run all callbacks registered for a hook. Returns list of results."""
        results = []
        for callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.warning('Plugin hook "%s" error: %s', hook_name, e)
                results.append(None)
        return results

    def run_filter_hooks(self, hook_name, value, *args, **kwargs):
        """Run callbacks as a filter chain, threading `value` through each.

        Each callback is invoked as `callback(value, *args, **kwargs)` and its
        return value (if a non-None string) becomes the `value` passed to the
        next callback. This allows multiple plugins to compose transformations
        of the same content instead of overwriting each other.

        Returns the final accumulated value.
        """
        for callback in self.hooks[hook_name]:
            try:
                result = callback(value, *args, **kwargs)
                if isinstance(result, str):
                    value = result
            except Exception as e:
                logger.warning('Plugin hook "%s" error: %s', hook_name, e)
        return value

    def register_shortcode(self, name, handler):
        """Register a shortcode via the shortcode registry."""
        if self.shortcode_registry:
            self.shortcode_registry.register(name, handler)

    def add_markdown_extension(self, extension):
        """Add a markdown extension for the build."""
        if extension not in self.markdown_extensions:
            self.markdown_extensions.append(extension)

    def add_jinja2_extension(self, extension):
        """Add a Jinja2 extension for the template environment."""
        if extension not in self.jinja2_extensions:
            self.jinja2_extensions.append(extension)

    def get_markdown_extensions(self):
        """Get all markdown extensions (built-in + plugin-provided)."""
        plugin_exts = []
        for exts in self.run_hooks('plugin_markdown_extensions'):
            if exts:
                plugin_exts.extend(exts)
        return self.markdown_extensions + plugin_exts

    def get_jinja2_extensions(self):
        """Get all Jinja2 extensions (registered + plugin-provided)."""
        ext_results = []
        for exts in self.run_hooks('plugin_jinja2_extensions'):
            if exts:
                ext_results.extend(exts)
        return self.jinja2_extensions + ext_results
