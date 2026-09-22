"""Development server with live reload capability."""

import functools
import logging
from pathlib import Path

from .builder import SiteBuilder
from .logging_utils import configure_logging
from .paths import package_templates_dir


logger = logging.getLogger(__name__)

try:
    from livereload import Server
    LIVERELOAD_AVAILABLE = True
except ImportError:
    LIVERELOAD_AVAILABLE = False


def serve(site_dir, output_dir, host='0.0.0.0', port=8000, debug=False):
    """Start the development server, rebuilding the site on source changes."""
    configure_logging(debug)
    site_dir = Path(site_dir).resolve()
    output_dir = Path(output_dir).resolve()

    if LIVERELOAD_AVAILABLE:
        print(f"Starting live reload server at http://{host}:{port}")

        def rebuild_site():
            logger.debug("[Live Reload] Rebuilding site...")
            try:
                builder = SiteBuilder(site_dir, output_dir)
                if builder.build():
                    logger.debug("[Live Reload] Site rebuilt successfully")
                else:
                    logger.debug("[Live Reload] Build failed")
            except Exception:
                logger.exception("[Live Reload] Build error")

        server = Server()

        watch_dirs = [
            package_templates_dir(),
            site_dir / 'templates',
            site_dir / 'config',
            site_dir / 'translations',
            site_dir / 'content',
            site_dir / 'sections',
            site_dir / 'posts',
            site_dir / 'drafts',
        ]
        for watch_dir in watch_dirs:
            if Path(watch_dir).exists():
                server.watch(str(watch_dir), rebuild_site)

        server.serve(root=str(output_dir), host=host, port=port)
    else:
        print("livereload not available, install with: pip install 'pagesmith[serve]'")
        print(f"Starting fallback HTTP server at http://{host}:{port}")
        print("Press Ctrl+C to stop")

        import http.server
        import socketserver

        if not output_dir.exists():
            logger.error("%s does not exist. Run 'pagesmith build' first.", output_dir)
            return 1

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(output_dir))

        try:
            with socketserver.TCPServer((host, port), handler) as httpd:
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

    return 0
