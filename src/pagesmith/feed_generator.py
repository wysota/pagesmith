"""
Feed and sitemap generation module.
Generates Atom/RSS feeds and XML sitemaps for SEO and content syndication.
"""

from pathlib import Path
from datetime import datetime, date, timezone
from xml.sax.saxutils import escape as xml_escape
from typing import Dict, Optional, Any, Callable
import logging


logger = logging.getLogger(__name__)


class FeedGenerator:
    """
    Generates RSS/Atom feeds and XML sitemaps for website.
    """
    
    def __init__(
        self,
        site_dir: Path,
        output_dir: Path,
        default_lang: str,
        config: Dict[str, Any],
        read_file_fn: Callable[[Path], str],
        parse_metadata_fn: Callable[[str], tuple],
        markdown_to_html_fn: Callable[[str], str],
    ):
        """
        Initialize FeedGenerator.
        
        Args:
            site_dir: Root site directory
            output_dir: Output build directory
            default_lang: Default language code
            config: Site configuration
            read_file_fn: Function to read file
            parse_metadata_fn: Function to parse metadata
            markdown_to_html_fn: Function to convert markdown to HTML
        """
        self.site_dir = site_dir
        self.output_dir = output_dir
        self.default_lang = default_lang
        self.config = config
        self.read_file = read_file_fn
        self.parse_metadata = parse_metadata_fn
        self.markdown_to_html = markdown_to_html_fn
    
    def _atom_date(self, date_val: Any) -> str:
        """
        Normalize a metadata date into an RFC 3339 timestamp for Atom feeds.
        Accepts datetime/date objects or strings (e.g. '2026-05-09').
        
        Args:
            date_val: Date value (datetime, date, or string)
            
        Returns:
            RFC 3339 formatted datetime string, empty string if unparseable
        """
        if not date_val:
            return ''

        # datetime.date / datetime.datetime
        if isinstance(date_val, datetime):
            dt = date_val if date_val.tzinfo else date_val.replace(tzinfo=timezone.utc)
            return dt.replace(microsecond=0).isoformat()
        if isinstance(date_val, date):
            return datetime(date_val.year, date_val.month, date_val.day,
                            tzinfo=timezone.utc).isoformat()

        # String forms
        s = str(date_val).strip()
        if not s:
            return ''
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
                return dt.replace(microsecond=0).isoformat()
            except ValueError:
                continue
        return ''

    def generate_rss(self) -> None:
        """Generate RSS/Atom feed from published posts in default language."""
        logger.debug("Generating RSS feed")
        
        posts_dir = self.site_dir / 'posts' / self.default_lang
        
        if not posts_dir.exists():
            logger.debug("No posts directory found")
            return
        
        # Get permalink pattern
        permalink_pattern = self.config['build'].get('permalink', 'posts/:slug')
        
        # Gather all published posts
        post_files = sorted(posts_dir.glob('*.md'), reverse=True)
        posts = []
        
        for post_file in post_files:
            # Parse filename: YYYY-MM-DD-slug.md
            filename = post_file.stem
            parts = filename.split('-', 3)
            
            if len(parts) < 4:
                continue
            
            year = parts[0]
            month = parts[1]
            day = parts[2]
            slug = parts[3]
            
            # Read and parse post
            post_content = self.read_file(post_file)
            metadata, content_markdown = self.parse_metadata(post_content)
            
            # Skip drafts
            if metadata.get('draft', False):
                continue
            
            # Extract title from metadata or markdown
            lines = content_markdown.strip().split('\n')
            if lines and lines[0].startswith('# '):
                page_title = lines[0].lstrip('# ').strip()
                content_markdown = '\n'.join(lines[1:])
            else:
                page_title = metadata.get('title', slug)
            
            # Convert to HTML
            page_content = self.markdown_to_html(content_markdown)
            
            # Build permalink path: replace placeholders in pattern
            permalink_path = permalink_pattern
            permalink_path = permalink_path.replace(':slug', slug)
            permalink_path = permalink_path.replace(':year', year)
            permalink_path = permalink_path.replace(':month', month)
            permalink_path = permalink_path.replace(':day', day)
            
            posts.append({
                'slug': slug,
                'title': metadata.get('title', page_title),
                'date': metadata.get('date', ''),
                'author': metadata.get('author', ''),
                'content': page_content,
                'permalink': permalink_path,
            })
        
        if not posts:
            logger.debug("No published posts found")
            return
        
        # Build Atom feed XML
        site_name = xml_escape(str(self.config['site'].get('name', 'Site')))
        base_url = self.config['site'].get('base_url', 'https://example.com').rstrip('/')
        base_url_x = xml_escape(base_url, {'"': '&quot;'})
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        
        feed_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>{site_name}</title>
    <link href="{base_url_x}"/>
    <link href="{base_url_x}/feed.xml" rel="self"/>
    <id>{base_url_x}</id>
    <updated>{now}</updated>
'''
        
        for post in posts:
            post_url = xml_escape(f"{base_url}/{post['permalink']}.html", {'"': '&quot;'})
            title = xml_escape(str(post['title']))
            updated = self._atom_date(post['date']) or now
            entry = f'''    <entry>
        <title>{title}</title>
        <link href="{post_url}"/>
        <id>{post_url}</id>
        <updated>{updated}</updated>
'''
            if post['author']:
                author = xml_escape(str(post['author']))
                entry += f'''        <author>
             <name>{author}</name>
         </author>
'''
            entry += f'''        <content type="html"><![CDATA[{post['content']}]]></content>
     </entry>
'''
            feed_xml += entry
        
        feed_xml += '</feed>\n'
        
        # Write feed file
        feed_path = self.output_dir / 'feed.xml'
        feed_path.parent.mkdir(parents=True, exist_ok=True)
        with open(feed_path, 'w', encoding='utf-8') as f:
            f.write(feed_xml)
        
        logger.debug("Generated %s", feed_path)
    
    def generate_sitemap(self) -> None:
        """Generate sitemap.xml from all HTML files in output directory."""
        logger.debug("Generating sitemap")
        
        if not self.output_dir.exists():
            logger.debug("Output directory not found")
            return
        
        # Walk output directory and collect all HTML files
        html_files = []
        for html_file in self.output_dir.rglob('*.html'):
            html_files.append(html_file)
        
        if not html_files:
            logger.debug("No HTML files found")
            return
        
        base_url = self.config['site'].get('base_url', 'https://example.com').rstrip('/')
        
        # Build sitemap XML
        sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
        
        for html_file in sorted(html_files):
            # Get relative path from output dir
            rel_path = html_file.relative_to(self.output_dir)
            # Convert Windows paths to forward slashes
            rel_path_str = str(rel_path).replace('\\', '/')
            
            # Build full URL
            if rel_path_str == 'index.html':
                page_url = base_url + '/'
            else:
                page_url = f"{base_url}/{rel_path_str}".replace('index.html', '').rstrip('/')
            
            sitemap_xml += f'''    <url>
         <loc>{xml_escape(page_url)}</loc>
     </url>
'''
        
        sitemap_xml += '</urlset>\n'
        
        # Write sitemap file
        sitemap_path = self.output_dir / 'sitemap.xml'
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_xml)
        
        logger.debug("Generated %s", sitemap_path)
