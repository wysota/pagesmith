"""
Mermaid diagram renderer plugin.

Renders Mermaid diagrams to SVG at build time using mmdc (mermaid-cli).
Supports:
  - Block shortcode:    {% mermaid %}...{% endmermaid %}
  - Inline shortcode:  {% mermaid file='diagram.mmd' %}
  - Fenced code block: ```mermaid ... ``` (converted to shortcode in build.py)

Optional shortcode kwargs: theme, backgroundColor, width, height, alt, caption

Prerequisites:
  npm install -g @mermaid-js/mermaid-cli
"""

import os
import re
import json
import hashlib
import subprocess
import tempfile
import html as html_module
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class MermaidRenderer:
    """Renders Mermaid source to SVG files using mmdc (mermaid-cli)."""

    def __init__(self, site_builder):
        self.site_builder = site_builder
        self.diagrams_dir = site_builder.site_dir / 'diagrams'
        self.images_dir = site_builder.images_dir   # sites/<name>/images/
        self.cache_file = self.diagrams_dir / '.mermaid_cache.json'
        self.cache = {}
        self._mmdc_checked = None
        self._ensure_dirs()
        self._load_cache()

    def _ensure_dirs(self):
        """Create diagrams/ and images/ directories if they don't exist."""
        self.diagrams_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def _puppeteer_config_path(self):
        """
        Return the path to a puppeteer config JSON that passes --no-sandbox.
        Written once on first call and reused. Needed on systems where
        unprivileged user namespaces are restricted (e.g. Ubuntu 23.10+ with AppArmor).
        """
        cfg_path = self.diagrams_dir / '.puppeteer.json'
        if not cfg_path.exists():
            cfg_path.write_text(
                json.dumps({"args": ["--no-sandbox"]}),
                encoding='utf-8'
            )
        return cfg_path

    def _load_cache(self):
        """Load hash-based render cache from .mermaid_cache.json."""
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text('utf-8'))
            except (json.JSONDecodeError, IOError):
                self.cache = {}

    def _save_cache(self):
        """Persist render cache to .mermaid_cache.json."""
        try:
            self.cache_file.write_text(json.dumps(self.cache, indent=2), 'utf-8')
        except IOError as e:
            logger.warning("Failed to save mermaid cache: %s", e)

    def _hash(self, text):
        """Return SHA-256 hex digest of text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _cache_key(self, source_text, opts):
        """Compute a cache key from source plus all settings that affect output.

        The render output depends not only on the diagram source but also on
        the mmdc options (theme, backgroundColor, width, height) and the
        post-processing max-width cap. Including them ensures changing any of
        these invalidates stale cached SVGs.
        """
        opts = opts or {}
        relevant = {k: opts[k] for k in sorted(opts) if opts[k] is not None}
        payload = json.dumps(
            {'src': source_text, 'opts': relevant, 'max_w': self.SVG_MAX_WIDTH_PX},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _check_mmdc(self):
        """Return True if mmdc is available on PATH."""
        if self._mmdc_checked is not None:
            return self._mmdc_checked
        try:
            result = subprocess.run(['mmdc', '--version'], capture_output=True, timeout=10)
            self._mmdc_checked = (result.returncode == 0)
            if not self._mmdc_checked:
                logger.warning("mmdc found but returned a non-zero exit code; diagrams will not be rendered")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._mmdc_checked = False
            logger.warning("mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli")
        return self._mmdc_checked

    def _run_mmdc(self, input_path, output_path, opts=None):
        """
        Run mmdc to render input_path -> output_path.
        opts: dict with optional keys: theme, backgroundColor, width, height.
        Returns the actual output path (mmdc may add -1 suffix on some versions).
        Raises subprocess.CalledProcessError or subprocess.TimeoutExpired on failure.
        """
        if opts is None:
            opts = {}
        cmd = ['mmdc', '-i', str(input_path), '-o', str(output_path),
               '-p', str(self._puppeteer_config_path())]
        for key, flag in [('theme', '-t'), ('backgroundColor', '-b'),
                          ('width', '-w'), ('height', '-H')]:
            if opts.get(key):
                cmd.extend([flag, str(opts[key])])
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)

        # Some mmdc versions write "stem-1.svg" instead of "stem.svg"
        if not output_path.exists():
            stem = output_path.stem
            parent = output_path.parent
            suffixed = parent / f'{stem}-1.svg'
            if suffixed.exists():
                suffixed.rename(output_path)

        # Clean up the SVG: remove baked-in background and cap intrinsic max-width
        if output_path.exists():
            self._postprocess_svg(output_path)

        return output_path

    SVG_MAX_WIDTH_PX = 700

    def _postprocess_svg(self, svg_path):
        """
        Post-process a rendered SVG file:
          1. Remove 'background-color' from the root <svg> element's style
             attribute so dark-mode pages show a transparent background.
          2. Cap the 'max-width' in the root style to SVG_MAX_WIDTH_PX.

        mmdc writes something like:
          <svg ... style="max-width: 955.38px; background-color: white;" ...>
        We want:
          <svg ... style="max-width: 800px;" ...>
        """
        try:
            text = svg_path.read_text('utf-8')

            def _fix_root_style(m):
                style_val = m.group(1)
                # Remove background-color property
                style_val = re.sub(
                    r'\s*background-color\s*:[^;]*;?\s*', ' ', style_val
                ).strip().strip(';').strip()
                # Cap or set max-width
                if re.search(r'max-width\s*:', style_val):
                    style_val = re.sub(
                        r'max-width\s*:\s*[\d.]+px',
                        f'max-width: {self.SVG_MAX_WIDTH_PX}px',
                        style_val
                    )
                else:
                    sep = '; ' if style_val else ''
                    style_val = f'max-width: {self.SVG_MAX_WIDTH_PX}px{sep}{style_val}'
                return f'style="{style_val.strip()}"'

            # Only touch the first <svg ...> opening tag
            # Match the style="..." attribute within it
            def _fix_svg_tag(tag_match):
                tag = tag_match.group(0)
                tag = re.sub(r'\bstyle="([^"]*)"', _fix_root_style, tag, count=1)
                return tag

            text = re.sub(r'<svg\b[^>]*>', _fix_svg_tag, text, count=1)
            svg_path.write_text(text, 'utf-8')
        except Exception as e:
            logger.warning("SVG post-processing failed for %s: %s", svg_path.name, e)

    def _render(self, source_text, output_name, input_path, opts, label):
        """Shared render pipeline: cache check, mmdc run, cache save.

        Args:
            source_text: Mermaid source (used for the cache key).
            output_name: Target SVG basename in images/.
            input_path: Existing .mmd path to render, or None to render from a
                temp file written from `source_text`.
            opts: dict of mmdc options (theme, backgroundColor, width, height).
            label: Human-readable label for error/warning messages.

        Returns:
            str: output_name on success/cache-hit, or None on failure.
        """
        opts = opts or {}
        key = self._cache_key(source_text, opts)
        output_path = self.images_dir / output_name

        # Cache hit: key matches (source + opts + max-width) and SVG exists.
        cached = self.cache.get(key)
        if cached and cached.get('output') == output_name and output_path.exists():
            return output_name

        if not self._check_mmdc():
            return None

        temp_path = None
        try:
            if input_path is None:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.mmd', delete=False, encoding='utf-8'
                ) as f:
                    f.write(source_text)
                    temp_path = f.name
                render_input = temp_path
            else:
                render_input = input_path

            self._run_mmdc(render_input, output_path, opts)
            self.cache[key] = {'output': output_name}
            self._save_cache()
            return output_name

        except subprocess.CalledProcessError as e:
            logger.warning("mermaid render failed (%s): %s", label, e.stderr)
        except subprocess.TimeoutExpired:
            logger.warning("mermaid render timed out (%s)", label)
        except Exception as e:
            logger.warning("mermaid render error (%s): %s", label, e)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        return None

    def render_mermaid(self, source_text, label='inline', **opts):
        """
        Render inline Mermaid source text to an SVG in images/.

        Args:
            source_text: Raw Mermaid diagram source.
            label: Human-readable label for error/warning messages.
            **opts: Optional mmdc options (theme, backgroundColor, width, height).

        Returns:
            str: SVG filename (e.g. 'mermaid_a1b2c3d4e5f6.svg'), or None on failure.
        """
        if not source_text.strip():
            return None

        # Filename derived from full cache key so different opts don't collide.
        output_name = f'mermaid_{self._cache_key(source_text, opts)[:12]}.svg'
        return self._render(source_text, output_name, None, opts, label)

    def render_file(self, filename, **opts):
        """
        Render an external .mmd file from diagrams/ to an SVG in images/.

        Args:
            filename: Basename of the .mmd file (e.g. 'flowchart.mmd').
            **opts: Optional mmdc options (theme, backgroundColor, width, height).

        Returns:
            str: SVG filename (e.g. 'flowchart.svg'), or None on failure.
        """
        file_path = self.diagrams_dir / filename
        if not file_path.exists():
            logger.warning("mermaid file not found: %s", file_path)
            return None

        source_text = file_path.read_text('utf-8')
        output_name = f'{file_path.stem}.svg'
        return self._render(source_text, output_name, file_path, opts, filename)

    def batch_render_external_files(self):
        """before_build hook: pre-render all .mmd files in diagrams/."""
        if not self.diagrams_dir.exists():
            return
        mmd_files = sorted(self.diagrams_dir.glob('*.mmd'))
        if mmd_files:
            logger.debug("Rendering %s mermaid diagram(s)", len(mmd_files))
            for f in mmd_files:
                self.render_file(f.name)


def register(plugin_manager):
    """Plugin entry point: register the mermaid shortcode and before_build hook."""
    if plugin_manager.site_builder is None:
        return

    renderer = MermaidRenderer(plugin_manager.site_builder)
    sb = plugin_manager.site_builder

    def mermaid_handler(args=None, kwargs=None, content=None):
        """
        Handler for the {% mermaid %} shortcode.

        Forms:
          {% mermaid file='diagram.mmd' %}
          {% mermaid %}...diagram source...{% endmermaid %}
          {% mermaid theme='dark' %}...{% endmermaid %}
        """
        if kwargs is None:
            kwargs = {}
        try:
            # Collect optional mmdc rendering options from kwargs
            mmdc_opts = {k: kwargs[k] for k in ('theme', 'backgroundColor', 'width', 'height')
                         if k in kwargs}

            if kwargs.get('file'):
                output_name = renderer.render_file(kwargs['file'], **mmdc_opts)
                desc = f"file '{kwargs['file']}'"
            elif content:
                output_name = renderer.render_mermaid(content.strip(), 'shortcode', **mmdc_opts)
                desc = 'inline shortcode'
            else:
                return ''

            if output_name is None:
                return f'<!-- mermaid render failed: {html_module.escape(desc)} -->'

            # Use absolute URL (relative to /) for images
            # This ensures images work correctly regardless of page depth or language subdirectory
            img_url = html_module.escape(f'/images/{output_name}', quote=True)
            alt = html_module.escape(kwargs.get('alt', 'Mermaid diagram'))
            caption = kwargs.get('caption', '')

            cap_html = ''
            if caption:
                cap_html = f'<figcaption>{html_module.escape(caption)}</figcaption>'

            return (
                f'<figure class="mermaid-diagram">'
                f'<img src="{img_url}" alt="{alt}" />'
                f'{cap_html}'
                f'</figure>'
            )
        except Exception as e:
            return f'<!-- mermaid shortcode error: {html_module.escape(str(e))} -->'

    plugin_manager.register_shortcode('mermaid', mermaid_handler)
    plugin_manager.register_hook('before_build', renderer.batch_render_external_files)
