"""Site content management: pages, languages, posts, drafts, export, status."""

import sys
import re
import logging
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

import yaml

from .paths import load_site_config, resolve_output_dir, scaffold_dir


logger = logging.getLogger(__name__)


def _content_file_name(entry):
    """Return the Markdown filename for an index ``content_files`` entry.

    Entries may be plain strings (``'hero.md'``) or the explicit mapping form
    (``{'hero': {'file': 'hero.md', 'format': 'hero'}}``); both resolve to the
    source file name used during the build.
    """
    if isinstance(entry, str):
        return entry
    name, cfg = next(iter(entry.items()))
    return cfg.get('file', f'{name}.md')


class LinkExtractor(HTMLParser):
    """Extract links from HTML content."""
    
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_file = None
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a' and 'href' in attrs_dict:
            self.links.append(('href', attrs_dict['href'], self.current_file))
        elif tag == 'img' and 'src' in attrs_dict:
            self.links.append(('src', attrs_dict['src'], self.current_file))
        elif tag == 'link' and 'href' in attrs_dict:
            self.links.append(('href', attrs_dict['href'], self.current_file))
        elif tag == 'script' and 'src' in attrs_dict:
            self.links.append(('src', attrs_dict['src'], self.current_file))


class SiteManager:
    """Manage site content, pages, and configuration."""
    
    def __init__(self, site_dir, output_dir=None):
        self.site_dir = Path(site_dir).resolve()
        self.site_name = self.site_dir.name
        self.config_path = self.site_dir / 'config' / 'site.yaml'
        self.config = load_site_config(self.site_dir)

        # Directory paths from config (config paths are relative to site_dir)
        self.content_dir = self.site_dir / self.config['build']['content_dir']
        self.sections_dir = self.site_dir / self.config['build']['sections_dir']
        self.output_dir = resolve_output_dir(
            self.site_dir, output=output_dir, config=self.config)
        self.translations_dir = self.site_dir / 'translations'
        self.drafts_dir = self.site_dir / 'drafts'
        self.posts_dir = self.site_dir / 'posts'

        # Languages
        self.languages = self.config['languages']
        self.default_lang = self.get_default_language()

    def save_config(self):
        """Save site configuration."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def get_default_language(self):
        """Get the default language code."""
        for code, lang in self.languages.items():
            if lang.get('default', False):
                return code
        return list(self.languages.keys())[0]
    
    # =========================================================================
    # Page Management
    # =========================================================================
    
    def add_page(self, name, title=None, add_to_nav=True):
        """Add a new section page to the site."""
        name = name.lower().replace(' ', '-')
        
        if name in self.config['pages']:
            print(f"Error: Page '{name}' already exists")
            return False
        
        if title is None:
            title = name.replace('-', ' ').title()
        
        # Add to config
        self.config['pages'][name] = {
            'template': 'page.html',
            'nav_name': name.upper().replace('-', ' '),
            'markdown': f'{name}.md',
            'section': True
        }
        
        # Create markdown files for each language
        for lang in self.languages:
            lang_dir = self.sections_dir / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            md_file = lang_dir / f'{name}.md'
            if not md_file.exists():
                content = f"# {title}\n\nAdd your content here.\n"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  Created {md_file}")
            else:
                print(f"  Skipped {md_file} (already exists)")
        
        # Add translation keys
        for lang in self.languages:
            self.add_nav_translation(lang, name, title)
        
        # Save config
        self.save_config()
        print(f"  Updated {self.config_path}")
        
        if add_to_nav:
            print(f"\nNOTE: To show this page in the navigation, add an item to the")
            print(f"'items:' list in your site's data/nav.yaml (navigation is")
            print(f"data-driven; see the navigation docs):")
            print(f'  - name: {name}')
        
        print(f"\n Page '{name}' created successfully!")
        print(f"Run 'pagesmith build --site-dir {self.site_dir}' to regenerate the site.")
        return True
    
    def add_nav_translation(self, lang, page_name, title):
        """Add navigation translation for a page."""
        trans_file = self.translations_dir / f'{lang}.yaml'
        
        if not trans_file.exists():
            print(f"  Warning: Translation file {trans_file} not found")
            return
        
        with open(trans_file, 'r', encoding='utf-8') as f:
            translations = yaml.safe_load(f) or {}
        
        if 'nav' not in translations:
            translations['nav'] = {}
        
        if page_name not in translations['nav']:
            translations['nav'][page_name] = title
            
            with open(trans_file, 'w', encoding='utf-8') as f:
                yaml.dump(translations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"  Added nav.{page_name} to {trans_file}")
    
    def remove_page(self, name, keep_files=False):
        """Remove a section page from the site."""
        name = name.lower()
        
        if name not in self.config['pages']:
            print(f"Error: Page '{name}' not found")
            return False
        
        if name == 'index':
            print("Error: Cannot remove the index page")
            return False
        
        # Remove from config
        del self.config['pages'][name]
        self.save_config()
        print(f"  Removed '{name}' from {self.config_path}")
        
        if not keep_files:
            # Remove markdown files
            for lang in self.languages:
                md_file = self.sections_dir / lang / f'{name}.md'
                if md_file.exists():
                    md_file.unlink()
                    print(f"  Deleted {md_file}")
        
        print(f"\nNOTE: You may want to remove the link from your site's templates/partials/nav.html.")
        print(f"\n Page '{name}' removed!")
        return True
    
    def list_pages(self):
        """List all configured pages."""
        print("Configured pages:\n")
        for name, config in self.config['pages'].items():
            page_type = "section" if config.get('section') else "index"
            print(f"  {name}")
            print(f"    Type: {page_type}")
            print(f"    Template: {config['template']}")
            if 'markdown' in config:
                print(f"    Markdown: {config['markdown']}")
            print()
    
    # =========================================================================
    # Language Management
    # =========================================================================
    
    def add_language(self, code, name):
        """Add a new language to the site."""
        code = code.lower()
        
        if code in self.languages:
            print(f"Error: Language '{code}' already exists")
            return False
        
        # Add to config
        self.config['languages'][code] = {
            'name': name,
            'code': code,
            'default': False
        }
        self.save_config()
        print(f"  Added language '{code}' to config")
        
        # Create translation file
        trans_file = self.translations_dir / f'{code}.yaml'
        if not trans_file.exists():
            # Copy from default language as template
            default_trans = self.translations_dir / f'{self.default_lang}.yaml'
            if default_trans.exists():
                with open(default_trans, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Add comment about translation needed
                content = f"# {name} UI Translations\n# TODO: Translate from {self.default_lang}\n" + \
                          '\n'.join(content.split('\n')[1:])
                with open(trans_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(trans_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {name} UI Translations\nnav:\n  home: \"Home\"\n")
            print(f"  Created {trans_file}")
        
        # Create content directories
        for subdir in [self.content_dir, self.sections_dir]:
            lang_dir = subdir / code
            lang_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Created {lang_dir}")
        
        print(f"\n Language '{code}' ({name}) added!")
        print(f"Populate content/{code}/ and sections/{code}/ with translated content.")
        print(f"Run 'pagesmith build --site-dir {self.site_dir}' to regenerate the site.")
        return True
    
    def list_languages(self):
        """List all configured languages."""
        print("Configured languages:\n")
        for code, config in self.languages.items():
            default = " (default)" if config.get('default') else ""
            print(f"  {code}: {config['name']}{default}")
    
    # =========================================================================
    # Translation Management
    # =========================================================================
    
    def translate_page(self, page, target_lang):
        """Create a translation stub for a page from the default language."""
        page = page.lower()
        target_lang = target_lang.lower()
        
        if target_lang not in self.languages:
            print(f"Error: Language '{target_lang}' not configured")
            return False
        
        if target_lang == self.default_lang:
            print(f"Error: Cannot translate to default language")
            return False
        
        # Determine source and target paths
        if page == 'index':
            # Homepage content files
            content_files = self.config['pages'].get('index', {}).get('content_files', [])
            if not content_files:
                print("Error: No content files configured for index page")
                return False
            
            for content_file in content_files:
                filename = _content_file_name(content_file)
                self._create_translation_stub(
                    self.content_dir / self.default_lang / filename,
                    self.content_dir / target_lang / filename,
                    target_lang
                )
        else:
            # Section page
            if page not in self.config['pages']:
                print(f"Error: Page '{page}' not found in config")
                return False
            
            page_config = self.config['pages'][page]
            if not page_config.get('section'):
                print(f"Error: Page '{page}' is not a section page")
                return False
            
            md_file = page_config.get('markdown', f'{page}.md')
            self._create_translation_stub(
                self.sections_dir / self.default_lang / md_file,
                self.sections_dir / target_lang / md_file,
                target_lang
            )
        
        return True
    
    def _create_translation_stub(self, source_path, target_path, target_lang):
        """Create a translation stub file."""
        if not source_path.exists():
            print(f"  Warning: Source file not found: {source_path}")
            return False
        
        if target_path.exists():
            print(f"  Skipped {target_path} (already exists)")
            return False
        
        # Read source content
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add translation marker
        lang_name = self.languages[target_lang]['name']
        header = f"<!-- TODO: Translate to {lang_name} -->\n\n"
        
        # Create target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write stub
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(header + content)
        
        print(f"  Created {target_path}")
        return True
    
    def sync_translations(self):
        """Find missing translation keys across all language files."""
        print("Checking translation files...\n")
        
        # Load all translation files
        translations = {}
        for lang in self.languages:
            trans_file = self.translations_dir / f'{lang}.yaml'
            if trans_file.exists():
                with open(trans_file, 'r', encoding='utf-8') as f:
                    translations[lang] = yaml.safe_load(f) or {}
            else:
                translations[lang] = {}
                print(f"  Warning: Missing translation file: {trans_file}")
        
        # Get all keys from default language
        default_keys = self._get_all_keys(translations.get(self.default_lang, {}))
        
        # Check each language
        missing_count = 0
        for lang in self.languages:
            if lang == self.default_lang:
                continue
            
            lang_keys = self._get_all_keys(translations.get(lang, {}))
            missing = default_keys - lang_keys
            
            if missing:
                print(f"  {lang} ({self.languages[lang]['name']}):")
                for key in sorted(missing):
                    print(f"    - {key}")
                    missing_count += 1
        
        if missing_count == 0:
            print(" All translation keys are present!")
        else:
            print(f"\nTotal missing keys: {missing_count}")
        
        return missing_count == 0
    
    def _get_all_keys(self, d, prefix=''):
        """Recursively get all keys from a nested dict."""
        keys = set()
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(self._get_all_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys
    
    # =========================================================================
    # Post Management (Blog/News)
    # =========================================================================
    
    def new_post(self, name, title=None):
        """Create a new dated post."""
        name = name.lower().replace(' ', '-')
        
        if title is None:
            title = name.replace('-', ' ').title()
        
        # Create posts directory structure
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        for lang in self.languages:
            lang_dir = self.posts_dir / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{date_str}-{name}.md"
            post_file = lang_dir / filename
            
            if post_file.exists():
                print(f"  Skipped {post_file} (already exists)")
                continue
            
            # Create post template
            content = f"""---
title: "{title}"
date: {date_str}
author: ""
draft: false
---

# {title}

Write your post content here.
"""
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Created {post_file}")
        
        print(f"\n Post '{name}' created!")
        print(f"Edit the files in posts/{{lang}}/{date_str}-{name}.md")
        return True
    
    def list_posts(self):
        """List all posts."""
        print("Posts:\n")
        
        if not self.posts_dir.exists():
            print("  No posts directory found.")
            print("  Use 'make new-post NAME=...' to create your first post.")
            return
        
        for lang in self.languages:
            lang_dir = self.posts_dir / lang
            if not lang_dir.exists():
                continue
            
            posts = sorted(lang_dir.glob('*.md'), reverse=True)
            if posts:
                print(f"  {self.languages[lang]['name']} ({lang}):")
                for post in posts:
                    # Try to extract title from frontmatter
                    title = post.stem
                    with open(post, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                        if match:
                            title = match.group(1)
                    print(f"    - {post.name}: {title}")
                print()
    
    # =========================================================================
    # Draft Management
    # =========================================================================
    
    def create_draft(self, name, title=None):
        """Create a draft page (not included in build)."""
        name = name.lower().replace(' ', '-')
        
        if title is None:
            title = name.replace('-', ' ').title()
        
        # Create drafts directory
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        
        for lang in self.languages:
            lang_dir = self.drafts_dir / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            draft_file = lang_dir / f'{name}.md'
            
            if draft_file.exists():
                print(f"  Skipped {draft_file} (already exists)")
                continue
            
            content = f"# {title}\n\nThis is a draft. Use 'make publish NAME={name}' to publish.\n"
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Created {draft_file}")
        
        print(f"\n Draft '{name}' created!")
        print(f"Edit files in drafts/{{lang}}/{name}.md")
        print(f"When ready, run 'make publish NAME={name}' to publish.")
        return True
    
    def publish_draft(self, name, add_to_nav=True):
        """Move a draft to sections and add to config."""
        name = name.lower().replace(' ', '-')
        
        # Check if draft exists
        found_drafts = False
        for lang in self.languages:
            draft_file = self.drafts_dir / lang / f'{name}.md'
            if draft_file.exists():
                found_drafts = True
                break
        
        if not found_drafts:
            print(f"Error: No draft found with name '{name}'")
            print(f"Looking in: {self.drafts_dir}/*/")
            return False
        
        if name in self.config['pages']:
            print(f"Error: Page '{name}' already exists in config")
            return False
        
        # Extract title from first draft file
        title = name.replace('-', ' ').title()
        for lang in self.languages:
            draft_file = self.drafts_dir / lang / f'{name}.md'
            if draft_file.exists():
                with open(draft_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        title = first_line[2:]
                break
        
        # Move draft files to sections
        for lang in self.languages:
            draft_file = self.drafts_dir / lang / f'{name}.md'
            if draft_file.exists():
                target_dir = self.sections_dir / lang
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / f'{name}.md'
                
                shutil.move(str(draft_file), str(target_file))
                print(f"  Moved {draft_file} -> {target_file}")
        
        # Add to config
        self.config['pages'][name] = {
            'template': 'page.html',
            'nav_name': name.upper().replace('-', ' '),
            'markdown': f'{name}.md',
            'section': True
        }
        self.save_config()
        print(f"  Added '{name}' to config")
        
        # Add translation keys
        for lang in self.languages:
            self.add_nav_translation(lang, name, title)
        
        if add_to_nav:
            print(f"\nNOTE: To show this page in the navigation, add an item to the")
            print(f"'items:' list in your site's data/nav.yaml (navigation is")
            print(f"data-driven; see the navigation docs):")
            print(f'  - name: {name}')
        
        print(f"\n Draft '{name}' published!")
        print(f"Run 'pagesmith build --site-dir {self.site_dir}' to regenerate the site.")
        return True
    
    def list_drafts(self):
        """List all draft pages."""
        print("Drafts:\n")
        
        if not self.drafts_dir.exists():
            print("  No drafts directory found.")
            print("  Use 'make draft NAME=...' to create a draft.")
            return
        
        drafts = set()
        for lang in self.languages:
            lang_dir = self.drafts_dir / lang
            if lang_dir.exists():
                for draft in lang_dir.glob('*.md'):
                    drafts.add(draft.stem)
        
        if drafts:
            for name in sorted(drafts):
                langs = []
                for lang in self.languages:
                    if (self.drafts_dir / lang / f'{name}.md').exists():
                        langs.append(lang)
                print(f"  {name} ({', '.join(langs)})")
        else:
            print("  No drafts found.")
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def list_taxonomies(self):
        """List all taxonomy terms with post counts."""
        print("Taxonomies:\n")

        taxonomies = self.config.get('taxonomies', {})
        if not taxonomies:
            print("  No taxonomies configured. Add 'taxonomies:' section to config/site.yaml")
            return

        term_counts = {}
        for tax_type in taxonomies:
            term_counts[tax_type] = {}

        for lang in self.languages:
            lang_dir = self.posts_dir / lang
            if not lang_dir.exists():
                continue

            for post_file in lang_dir.glob('*.md'):
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                meta_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if not meta_match:
                    continue

                try:
                    metadata = yaml.safe_load(meta_match.group(1)) or {}
                except Exception as e:
                    logger.warning("Skipping %s: invalid metadata: %s", post_file.name, e)
                    continue

                for tax_type in taxonomies:
                    terms = metadata.get(tax_type, [])
                    if isinstance(terms, str):
                        terms = [t.strip() for t in terms.split(',') if t.strip()]
                    elif not isinstance(terms, list):
                        continue

                    for term in terms:
                        term = str(term).strip()
                        if term:
                            if term not in term_counts[tax_type]:
                                term_counts[tax_type][term] = {'count': 0, 'langs': set()}
                            term_counts[tax_type][term]['count'] += 1
                            term_counts[tax_type][term]['langs'].add(lang)

        for tax_type, terms in term_counts.items():
            plural = taxonomies[tax_type].get('plural', tax_type)
            print(f"  {plural.capitalize()}:")
            if terms:
                for name, info in sorted(terms.items()):
                    langs_str = ', '.join(sorted(info['langs']))
                    print(f"    {name} ({info['count']} posts, languages: {langs_str})")
            else:
                print(f"    (no terms found)")
            print()

    def check_content(self):
        """Check for missing content files."""
        print("Checking content files...\n")
        missing = []
        
        for lang in self.languages:
            # Check section pages
            for page_name, page_config in self.config['pages'].items():
                if page_config.get('section') and 'markdown' in page_config:
                    md_file = self.sections_dir / lang / page_config['markdown']
                    if not md_file.exists():
                        missing.append(str(md_file))
            
            # Check homepage content
            if 'index' in self.config['pages']:
                for content_file in self.config['pages']['index'].get('content_files', []):
                    content_path = self.content_dir / lang / _content_file_name(content_file)
                    if not content_path.exists():
                        missing.append(str(content_path))
        
        if missing:
            print("Missing content files:")
            for f in missing:
                print(f"  - {f}")
            return False
        else:
            print(" All content files present!")
            return True
    
    def validate_yaml(self):
        """Validate all YAML files in the project."""
        print("Validating YAML files...\n")
        
        yaml_files = []
        yaml_files.extend(self.site_dir.glob('config/*.yaml'))
        yaml_files.extend(self.site_dir.glob('translations/*.yaml'))
        yaml_files.extend(self.site_dir.glob('data/*.yaml'))
        yaml_files.extend(self.site_dir.glob('data/*.yml'))
        
        errors = []
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print(f"  OK: {yaml_file.relative_to(self.site_dir)}")
            except yaml.YAMLError as e:
                errors.append((yaml_file, str(e)))
                print(f"  ERROR: {yaml_file.relative_to(self.site_dir)}")
                print(f"         {e}")
        
        print()
        if errors:
            print(f"Found {len(errors)} YAML error(s)")
            return False
        else:
            print(" All YAML files are valid!")
            return True
    
    def check_links(self):
        """Check for broken internal links in generated HTML."""
        print("Checking links in generated HTML...\n")
        
        if not self.output_dir.exists():
            print("Error: Output directory not found. Run 'pagesmith build' first.")
            return False
        
        # Collect all HTML files and their links
        extractor = LinkExtractor()
        html_files = list(self.output_dir.rglob('*.html'))
        
        for html_file in html_files:
            with open(html_file, 'r', encoding='utf-8') as f:
                extractor.current_file = html_file
                try:
                    extractor.feed(f.read())
                except Exception as e:
                    print(f"  Warning: Could not parse {html_file}: {e}")
        
        # Check each link
        broken = []
        external = []
        
        for link_type, link, source_file in extractor.links:
            # Skip empty, anchors, mailto, tel, javascript
            if not link or link.startswith('#') or link.startswith('mailto:') or \
               link.startswith('tel:') or link.startswith('javascript:'):
                continue
            
            # Parse the URL
            parsed = urlparse(link)
            
            # External link
            if parsed.scheme in ('http', 'https'):
                external.append((link, source_file))
                continue
            
            # Resolve relative path
            if parsed.path:
                if parsed.path.startswith('/'):
                    # Absolute path from root
                    target = self.output_dir / parsed.path.lstrip('/')
                else:
                    # Relative path
                    target = source_file.parent / parsed.path
                
                # Normalize and check
                try:
                    target = target.resolve()
                    # Handle directory index
                    if target.is_dir():
                        target = target / 'index.html'
                    
                    if not target.exists():
                        rel_source = source_file.relative_to(self.output_dir)
                        broken.append((link, str(rel_source)))
                except Exception as e:
                    rel_source = source_file.relative_to(self.output_dir)
                    logger.warning(
                        "Could not resolve link %s from %s: %s", link, rel_source, e
                    )
                    broken.append((link, str(rel_source)))
        
        # Report results
        if broken:
            print("Broken internal links:")
            for link, source in broken:
                print(f"  {source}: {link}")
            print()
        
        print(f"Internal links checked: {len(extractor.links) - len(external)}")
        print(f"External links found: {len(external)} (not checked)")
        
        if broken:
            print(f"\n{len(broken)} broken link(s) found")
            return False
        else:
            print("\n All internal links OK!")
            return True
    
    # =========================================================================
    # Export
    # =========================================================================
    
    def export_site(self, output_name=None):
        """Export the site source as a ZIP archive.

        The archive contains the site's own source (config, content, templates,
        translations, data, assets, ...), excluding generated output and caches.
        """
        from . import __version__

        if output_name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"site_export_{timestamp}.zip"

        if not output_name.endswith('.zip'):
            output_name += '.zip'

        output_path = Path(output_name).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path

        print(f"Exporting site to {output_path}...\n")

        skip_dirs = {'__pycache__', '.git'}
        try:
            output_rel = self.output_dir.relative_to(self.site_dir)
        except ValueError:
            output_rel = None

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(self.site_dir.rglob('*')):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(self.site_dir)
                if any(part in skip_dirs for part in rel.parts):
                    continue
                if output_rel is not None and output_rel in rel.parents:
                    continue
                if file_path.name in ('.mermaid_cache.json', '.puppeteer.json'):
                    continue
                zf.write(file_path, rel)
                print(f"  Added {rel}")

            zf.writestr(
                'pagesmith-version.txt',
                f"pagesmith {__version__}\nsite: {self.site_name}\n",
            )
            print("  Added pagesmith-version.txt")

        size_kb = output_path.stat().st_size / 1024
        print(f"\n Exported to {output_path} ({size_kb:.1f} KB)")
        return True
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def show_status(self):
        """Show site status overview."""
        print("Site Status\n")
        print(f"Languages: {len(self.languages)}")
        for code, config in self.languages.items():
            default = " (default)" if config.get('default') else ""
            print(f"  - {config['name']} ({code}){default}")
        
        print(f"\nPages: {len(self.config['pages'])}")
        for name in self.config['pages']:
            print(f"  - {name}")
        
        # Check for drafts
        if self.drafts_dir.exists():
            drafts = set()
            for lang_dir in self.drafts_dir.iterdir():
                if lang_dir.is_dir():
                    for draft in lang_dir.glob('*.md'):
                        drafts.add(draft.stem)
            if drafts:
                print(f"\nDrafts: {len(drafts)}")
                for name in sorted(drafts):
                    print(f"  - {name}")
        
        # Check for posts
        if self.posts_dir.exists():
            post_count = 0
            for lang_dir in self.posts_dir.iterdir():
                if lang_dir.is_dir():
                    post_count += len(list(lang_dir.glob('*.md')))
            if post_count:
                print(f"\nPosts: {post_count // len(self.languages)} (across {len(self.languages)} languages)")
        
        print()
        self.check_content()


def create_site(name, title=None, base_dir=None):
    """Create a new site with default configuration.

    The site is created at ``<base_dir>/<name>`` where ``base_dir`` defaults to
    the current working directory.
    """
    base_dir = Path(base_dir).expanduser() if base_dir else Path.cwd()
    site_dir = (base_dir / name).resolve()
    if site_dir.exists():
        print(f"Error: Site '{name}' already exists at {site_dir}")
        sys.exit(1)

    if title is None:
        title = name.replace('-', ' ').title()

    config_dir = site_dir / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default site.yaml
    config = {
        'site': {'name': title, 'base_url': f'https://{name}.example.com'},
        'languages': {
            'en': {'name': 'English', 'code': 'en', 'default': True},
        },
        'taxonomies': {
            'tags': {'singular': 'tag', 'plural': 'tags', 'slug': 'tags', 'enabled': False},
            'categories': {'singular': 'category', 'plural': 'categories', 'slug': 'categories', 'enabled': False},
        },
        'pages': {
            'index': {'template': 'index.html', 'content_files': ['index.md']},
        },
    }
    with open(config_dir / 'site.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  Created {config_dir / 'site.yaml'}")

    # Create content directories with language subdirectories
    for subdir in ['content', 'sections', 'posts', 'data', 'images', 'assets', 'translations']:
        (site_dir / subdir).mkdir(parents=True, exist_ok=True)
    # Create default language subdirectories under content, sections, posts
    for subdir in ['content', 'sections', 'posts']:
        (site_dir / subdir / 'en').mkdir(parents=True, exist_ok=True)

    # Copy the package's minimal starter assets (CSS, JS, favicon)
    assets_src = scaffold_dir() / 'assets'
    if assets_src.is_dir():
        shutil.copytree(assets_src, site_dir / 'assets', dirs_exist_ok=True)
        print(f"  Created {site_dir / 'assets'}")

    def write_file(rel_path, content):
        path = site_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Created {path}")

    # UI translations used by the shared templates
    translations = {
        'footer': {'copyright': 'All rights reserved.'},
    }
    with open(site_dir / 'translations' / 'en.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(translations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  Created {site_dir / 'translations' / 'en.yaml'}")

    # Homepage content (a single Markdown file: first heading = title, body = content)
    write_file('content/en/index.md', (
        f"# {title}\n\n"
        "Placeholder content. Edit `content/en/index.md` to change this page.\n"
    ))

    print(f"\n Site '{name}' created at {site_dir}")
    print(f"Edit the content, then run 'pagesmith build --site-dir {site_dir}'")
    return site_dir

