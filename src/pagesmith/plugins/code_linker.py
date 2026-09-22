"""
Code linker plugin for static site generator.

Post-processes HTML to inject hyperlinks to external documentation for
identifiers found in code blocks and inline code elements.
"""

import re
import html as html_module
from pathlib import Path
from typing import Dict, List, Optional, Any


class CodeLinker:
    """Hyperlinks identifiers in code to external documentation."""

    def __init__(self, site_builder):
        """Initialize with site builder reference."""
        self.site_builder = site_builder
        self.link_schemes: Dict[str, Dict[str, Any]] = {}
        self.linker_options: Dict[str, Any] = {
            'link_class': 'code-link',
            'skip_existing_links': True,
            'verbose': False,
        }
        # CPPReference mapper for automatic C++ std library linking
        self.cppreference_mapper = None
        self.cppreference_enabled = False
        # Per-site config only; the package ships no project-wide link_schemes.yaml.
        self.config_path = Path(site_builder.site_dir) / 'config' / 'link_schemes.yaml'

    def load_config(self):
        """Load link schemes from config file."""
        if not self.config_path.exists():
            return

        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load {self.config_path}: {e}")
            return

        # Load link schemes
        self.link_schemes = config.get('link_schemes', {})

        # Load linker options
        options = config.get('linker_options', {})
        self.linker_options.update(options)

        # Initialize CPPReference mapper if enabled
        cppreference_config = config.get('cppreference', {})
        if cppreference_config.get('enabled', False):
            try:
                # Absolute import: plugins may be exec'd under a non-package
                # module name by PluginManager, where relative imports would fail.
                from pagesmith.plugins.cppreference_mapper import get_mapper

                self.cppreference_enabled = True
                cache_dir = cppreference_config.get('cache_dir')
                if cache_dir:
                    cache_dir = Path(cache_dir)

                self.cppreference_mapper = get_mapper(cache_dir)
                force_refresh = cppreference_config.get('force_refresh', False)
                self.cppreference_mapper.load(force_refresh=force_refresh)
            except Exception as e:
                print(f"Warning: Failed to initialize CPPReference mapper: {e}")
                self.cppreference_enabled = False

        # Compile patterns
        for scheme_name, scheme in self.link_schemes.items():
            if not scheme.get('enabled', True):
                continue

            pattern_str = scheme.get('pattern')
            if not pattern_str:
                print(f"Warning: Scheme '{scheme_name}' has no pattern")
                continue

            try:
                scheme['_compiled_pattern'] = re.compile(pattern_str)
            except re.error as e:
                print(f"Warning: Failed to compile pattern for scheme '{scheme_name}': {e}")

    def register_hook(self, plugin_manager):
        """Register the after_content_parse hook."""
        plugin_manager.register_hook('after_content_parse', self.process_html)

    def process_html(self, html_output: str, markdown_text: str = '') -> str:
        """
        Post-process HTML to inject links into code elements.

        Invoked as an `after_content_parse` filter hook: the HTML being
        threaded through the filter chain is the first argument.

        Args:
            html_output: Generated HTML content (threaded filter value)
            markdown_text: Original markdown content (informational)

        Returns:
            Modified HTML with links injected
        """
        if not self.link_schemes:
            return html_output

        # Find all code elements
        code_elements = self._find_code_elements(html_output)

        if not code_elements:
            return html_output

        # Process each code element (in reverse to preserve positions)
        for element_info in reversed(code_elements):
            html_output = self._process_code_element(html_output, element_info)

        return html_output

    def _find_code_elements(self, html_output: str) -> List[Dict[str, Any]]:
        """
        Find all code elements in HTML.

        Returns list of dicts with 'start', 'end', 'inner_start', 'inner_end', 'type'.
        """
        elements = []

        # Find <pre><code>...</code></pre> (block code)
        for match in re.finditer(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', html_output, re.DOTALL):
            elements.append({
                'start': match.start(),
                'end': match.end(),
                'inner_start': match.start(1),
                'inner_end': match.end(1),
                'type': 'block',
            })

        # Find <div class="codehilite">...</div> (Pygments)
        for match in re.finditer(r'<div[^>]*class="[^"]*codehilite[^"]*"[^>]*>(.*?)</div>', html_output, re.DOTALL):
            elements.append({
                'start': match.start(),
                'end': match.end(),
                'inner_start': match.start(1),
                'inner_end': match.end(1),
                'type': 'pygments',
            })

        # Find inline <code>...</code> (not in <pre>)
        for match in re.finditer(r'<code[^>]*>(.*?)</code>', html_output, re.DOTALL):
            before = html_output[:match.start()]
            open_pre = before.rfind('<pre')
            close_pre = before.rfind('</pre>')
            if open_pre > close_pre:
                continue
            elements.append({
                'start': match.start(),
                'end': match.end(),
                'inner_start': match.start(1),
                'inner_end': match.end(1),
                'type': 'inline',
            })

        return self._dedupe_overlapping(elements)

    @staticmethod
    def _dedupe_overlapping(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping/nested code elements, keeping the outermost.

        A Pygments code block emits ``<div class="codehilite"><pre><code>...``
        which is matched by both the ``pygments`` and ``block`` patterns, and a
        codehilite ``<div>`` also contains nested ``<pre><code>``. Processing
        overlapping regions corrupts offsets, so we keep only the widest,
        non-overlapping spans (outermost wins).
        """
        if not elements:
            return elements

        # Widest spans first so an enclosing element is chosen over nested ones.
        ordered = sorted(elements, key=lambda e: (e['start'], -(e['end'] - e['start'])))
        kept: List[Dict[str, Any]] = []
        covered_end = -1
        for el in ordered:
            if el['start'] >= covered_end:
                kept.append(el)
                covered_end = el['end']
            # else: starts inside an already-kept region -> skip (nested/overlap)
        return kept

    def _process_code_element(self, html_output: str, element_info: Dict[str, Any]) -> str:
        """Process a single code element to inject links."""
        inner_html = html_output[element_info['inner_start']:element_info['inner_end']]

        # Split into segments (tags vs text)
        segments = self._split_into_segments(inner_html)

        # Process text segments for linking
        modified_segments = self._link_segments(segments)

        # Reassemble
        modified_inner = ''.join(seg['content'] for seg in modified_segments)

        # Replace in original HTML
        html_output = (
            html_output[:element_info['inner_start']] +
            modified_inner +
            html_output[element_info['inner_end']:]
        )

        return html_output

    def _split_into_segments(self, inner_html: str) -> List[Dict[str, Any]]:
        """
        Split HTML into tag and text segments.

        Returns list of dicts with 'type' ('tag' or 'text') and 'content'.
        """
        segments = []
        pos = 0

        for match in re.finditer(r'<[^>]+>', inner_html):
            # Text before the tag
            if match.start() > pos:
                segments.append({
                    'type': 'text',
                    'content': inner_html[pos:match.start()],
                })
            # The tag itself
            segments.append({
                'type': 'tag',
                'content': match.group(),
            })
            pos = match.end()

        # Text after the last tag
        if pos < len(inner_html):
            segments.append({
                'type': 'text',
                'content': inner_html[pos:],
            })

        return segments

    def _link_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process text segments to inject links.

        Modifies segments in place and returns them.
        """
        in_link = False

        for segment in segments:
            if segment['type'] == 'tag':
                # Track if we're inside an <a> tag
                if segment['content'].startswith('<a'):
                    in_link = True
                elif segment['content'].startswith('</a'):
                    in_link = False
                continue

            # Skip text inside existing links if configured
            if in_link and self.linker_options.get('skip_existing_links', True):
                continue

            segment['content'] = self._linkify_text(segment['content'])

        return segments

    def _linkify_text(self, text: str) -> str:
        """
        Apply all link schemes to text and inject links.

        Processes matches in reverse order to preserve offsets.
        """
        matches = []

        # Collect all matches from all schemes
        for scheme_name, scheme in self.link_schemes.items():
            if not scheme.get('enabled', True):
                continue

            if '_compiled_pattern' not in scheme:
                continue

            pattern = scheme['_compiled_pattern']

            for match in pattern.finditer(text):
                matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(),
                    'groups': match.groupdict(),
                    'match_obj': match,
                    'scheme': scheme,
                })

        if not matches:
            return text

        # Deduplicate: sort by position, keep non-overlapping (first wins)
        matches.sort(key=lambda m: (m['start'], m['end']))
        deduplicated = []
        last_end = 0

        for match in matches:
            if match['start'] >= last_end:
                deduplicated.append(match)
                last_end = match['end']

        # Process in reverse order to preserve offsets
        for match in reversed(deduplicated):
            url = self._format_url(match['scheme'], match['groups'], match['match_obj'])
            if not url:
                continue

            link = self._create_link(match['text'], url)
            text = text[:match['start']] + link + text[match['end']:]

        return text

    # String methods permitted in transform expressions. Limited to safe,
    # pure, string-returning methods to avoid arbitrary code execution.
    _ALLOWED_STR_METHODS = {
        'lower', 'upper', 'title', 'capitalize', 'casefold',
        'strip', 'lstrip', 'rstrip', 'swapcase', 'replace',
    }

    # group  OR  group.method('arg', "arg2", ...)  with chained calls allowed.
    _TRANSFORM_RE = re.compile(
        r"""^\s*
            (?P<base>[A-Za-z_]\w*)                 # base group name
            (?P<calls>(?:\.\w+\((?:[^()]*)\))*)    # zero or more .method(...) calls
            \s*$""",
        re.VERBOSE,
    )
    _CALL_RE = re.compile(r"\.(\w+)\(([^()]*)\)")
    _STR_ARG_RE = re.compile(r"""\s*(?:"([^"]*)"|'([^']*)')\s*""")

    def _eval_transform(self, expr: str, groups: Dict[str, str]) -> str:
        """Safely evaluate a transform expression.

        Replaces the previous ``eval()`` based implementation. Supports only:
          - a bare group reference:        ``name``
          - whitelisted str-method chains: ``name.lower()``, ``name.replace('a','b').upper()``

        Method arguments must be quoted string literals. Anything else raises
        ValueError, which the caller treats as a failed transform.
        """
        m = self._TRANSFORM_RE.match(expr)
        if not m:
            raise ValueError(f"Unsupported transform expression: {expr!r}")

        base = m.group('base')
        if base not in groups:
            raise ValueError(f"Unknown group in transform: {base!r}")

        value = groups[base]
        if value is None:
            value = ''

        calls = m.group('calls')
        for call in self._CALL_RE.finditer(calls):
            method_name = call.group(1)
            if method_name not in self._ALLOWED_STR_METHODS:
                raise ValueError(f"Disallowed method in transform: {method_name!r}")

            raw_args = call.group(2).strip()
            args: List[str] = []
            if raw_args:
                for part in raw_args.split(','):
                    arg_match = self._STR_ARG_RE.fullmatch(part)
                    if not arg_match:
                        raise ValueError(
                            f"Transform args must be quoted strings: {part!r}"
                        )
                    args.append(arg_match.group(1)
                                if arg_match.group(1) is not None
                                else arg_match.group(2))

            method = getattr(str, method_name)
            value = method(value, *args)

        return value

    def _format_url(self, scheme: Dict[str, Any], groups: Dict[str, str], match_obj: Any) -> Optional[str]:
        """
        Format URL from scheme template and groups.

        Returns URL or None if formatting fails.
        """
        url_type = scheme.get('url_type', 'template')

        # Handle cppreference lookups
        if url_type == 'cppreference' and self.cppreference_enabled and self.cppreference_mapper:
            symbol = match_obj.group()
            cpref_type = scheme.get('cppreference_type', 'cpp')
            
            if cpref_type == 'cpp':
                url = self.cppreference_mapper.lookup_std_symbol(symbol)
            elif cpref_type == 'c':
                url = self.cppreference_mapper.lookup_c_symbol(symbol)
            else:
                url = self.cppreference_mapper.lookup(symbol, lang=cpref_type)
            
            if url:
                return url
            # Fall through to template-based formatting if lookup failed

        url_template = scheme.get('url', '')
        if not url_template:
            return None

        # Add full match as '_'
        groups['_'] = match_obj.group()

        # Apply transforms
        transformed = {}
        transforms = scheme.get('transform', {})

        for var_name, expr in transforms.items():
            try:
                transformed[var_name] = self._eval_transform(expr, groups)
            except Exception as e:
                if self.linker_options.get('verbose', False):
                    print(f"Warning: Transform '{expr}' failed: {e}")
                transformed[var_name] = groups.get(var_name, '')

        # Merge groups and transformed values
        all_values = {**groups, **transformed}

        # Format URL
        try:
            url = url_template.format(**all_values)
            return url
        except Exception as e:
            if self.linker_options.get('verbose', False):
                print(f"Warning: URL formatting failed: {e}")
            return None

    def _create_link(self, text: str, url: str) -> str:
        """Create an HTML link element."""
        link_class = self.linker_options.get('link_class', 'code-link')
        escaped_url = html_module.escape(url, quote=True)
        escaped_text = html_module.escape(text)
        return f'<a href="{escaped_url}" class="{link_class}" data-code-link>{escaped_text}</a>'


def register(plugin_manager):
    """Entry point for plugin loading."""
    code_linker = CodeLinker(plugin_manager.site_builder)
    code_linker.load_config()
    code_linker.register_hook(plugin_manager)
