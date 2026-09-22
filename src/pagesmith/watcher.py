"""File watcher for automatic site regeneration.

Monitors content, templates, and config files for changes and rebuilds on
modification.
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from .builder import SiteBuilder
from .logging_utils import configure_logging
from .paths import package_templates_dir

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    logging.getLogger(__name__).error("watchdog is required for watch mode")
    logging.getLogger(__name__).error("Install it with: pip install 'pagesmith[watch]'")
    sys.exit(1)


logger = logging.getLogger(__name__)


def _display(path):
    """Best-effort path relative to cwd, falling back to the raw path."""
    try:
        return Path(path).relative_to(Path.cwd())
    except ValueError:
        return Path(path)


class SiteRebuilder(FileSystemEventHandler):
    """Watch for file changes and trigger rebuilds."""

    def __init__(self, builder):
        self.builder = builder
        self.last_rebuild = 0
        self.debounce_delay = 2.0
        self.watch_patterns = [
            '.md',
            '.yaml',
            '.html',
            '.jinja2',
        ]
        self.ignore_dirs = {
            '.git',
            '__pycache__',
            'html',
            '.venv',
            'venv',
        }

    def should_process(self, path):
        path_obj = Path(path)
        for ignore_dir in self.ignore_dirs:
            if ignore_dir in path_obj.parts:
                return False
        return any(path.endswith(pattern) for pattern in self.watch_patterns)

    def should_rebuild(self):
        current_time = time.time()
        if current_time - self.last_rebuild >= self.debounce_delay:
            self.last_rebuild = current_time
            return True
        return False

    def rebuild(self, reason=""):
        if not self.should_rebuild():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.debug("[%s] File changed%s, rebuilding...", timestamp, reason)

        try:
            self.builder.translation_manager.clear_cache()

            success = self.builder.build()
            if success:
                logger.debug("[%s] Rebuild successful! Waiting for changes...", datetime.now().strftime('%H:%M:%S'))
            else:
                logger.debug("[%s] Rebuild failed. Waiting for changes...", datetime.now().strftime('%H:%M:%S'))
        except Exception:
            logger.exception("[%s] Rebuild error", datetime.now().strftime('%H:%M:%S'))

    def on_modified(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            self.rebuild(f": {_display(event.src_path)}")

    def on_created(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            self.rebuild(f" (new): {_display(event.src_path)}")


def watch(site_dir, output_dir, debug=False):
    """Watch the site and package template sources, rebuilding on changes."""
    configure_logging(debug)
    site_dir = Path(site_dir).resolve()
    output_dir = Path(output_dir).resolve()

    print("Starting site watcher...")
    print("Watching for changes in: content/, sections/, templates/, config/, translations/")
    print(f"Site: {site_dir}")
    print("Press Ctrl+C to stop\n")

    try:
        builder = SiteBuilder(site_dir, output_dir)
        logger.debug("Initial build")
        builder.build()
        logger.debug("[%s] Initial build complete! Watching for changes...", datetime.now().strftime('%H:%M:%S'))

        event_handler = SiteRebuilder(builder)
        observer = Observer()

        watch_dirs = [
            package_templates_dir(),
            site_dir / 'templates',
            site_dir / 'content',
            site_dir / 'sections',
            site_dir / 'config',
            site_dir / 'translations',
            site_dir / 'posts',
            site_dir / 'drafts',
        ]

        for watch_path in watch_dirs:
            if watch_path.exists():
                observer.schedule(event_handler, str(watch_path), recursive=True)

        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping watcher...")
            observer.stop()

        observer.join()
        print("Watcher stopped.")

    except FileNotFoundError as e:
        logger.exception("%s", e)
        return 1
    except Exception as e:
        logger.exception("%s", e)
        return 1
    return 0
