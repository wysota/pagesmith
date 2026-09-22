"""Command-line interface for pagesmith.

Single entry point with subcommands.  Site-wide options (``--site``,
``--site-dir``, ``--output``, ``--debug``) may be passed before or after the
subcommand.
"""

import argparse
import sys

from . import __version__
from .builder import SiteBuilder
from .logging_utils import configure_logging
from .manager import SiteManager, create_site
from .paths import (
    ConfigError,
    load_site_config,
    resolve_output_dir,
    resolve_site_dir,
)

def _add_common(parser, suppress):
    default = argparse.SUPPRESS if suppress else None
    parser.add_argument(
        '--site', default=default,
        help='Site name (looked up under ./sites/ or the repo sites/)')
    parser.add_argument(
        '--site-dir', dest='site_dir', default=default,
        help='Path to a site directory containing config/site.yaml')
    parser.add_argument(
        '--debug', action='store_true',
        default=(argparse.SUPPRESS if suppress else False),
        help='Enable debug logging')


def _add_output(parser, suppress):
    parser.add_argument(
        '--output', dest='output_dir',
        default=(argparse.SUPPRESS if suppress else None),
        help='Output directory (overrides site.yaml and PAGESMITH_OUTPUT)')


def _common_parent(suppress, with_output=True):
    parser = argparse.ArgumentParser(add_help=False)
    _add_common(parser, suppress)
    if with_output:
        _add_output(parser, suppress)
    return parser


def build_parser():
    parser = argparse.ArgumentParser(
        prog='pagesmith',
        description='Multi-language static site generator',
        parents=[_common_parent(suppress=False)],
    )
    parser.add_argument(
        '--version', action='version', version=f'pagesmith {__version__}')

    sub = parser.add_subparsers(dest='command', metavar='COMMAND')
    site_parent = _common_parent(suppress=True)

    def add(name, help_text):
        return sub.add_parser(name, help=help_text, parents=[site_parent])

    build_p = add('build', 'Build the site')
    build_p.add_argument(
        'site_name', nargs='?', metavar='SITE',
        help='Site name (shorthand for --site)')
    serve_p = add('serve', 'Start a development server')
    serve_p.add_argument(
        'site_name', nargs='?', metavar='SITE',
        help='Site name (shorthand for --site)')
    serve_p.add_argument('--host', default='0.0.0.0', help='Bind host')
    serve_p.add_argument('--port', type=int, default=8000, help='Bind port')
    watch_p = add('watch', 'Watch for changes and rebuild')
    watch_p.add_argument(
        'site_name', nargs='?', metavar='SITE',
        help='Site name (shorthand for --site)')

    add_site_p = sub.add_parser('add-site', help='Create a new site')
    add_site_p.add_argument('name', help='Site name')
    add_site_p.add_argument('--title', help='Site title (defaults to site name)')
    add_site_p.add_argument('--dir', help='Parent directory (defaults to cwd)')

    add_page_p = add('add-page', 'Add a new section page')
    add_page_p.add_argument('name', help='Page name (e.g., portfolio, blog)')
    add_page_p.add_argument('--title', help='Page title (defaults to capitalized name)')
    add_page_p.add_argument('--no-nav', action='store_true', help='Do not add to navigation')

    remove_page_p = add('remove-page', 'Remove a section page')
    remove_page_p.add_argument('name', help='Page name to remove')
    remove_page_p.add_argument('--keep-files', action='store_true', help='Keep markdown files')

    add('list-pages', 'List all configured pages')

    add_lang_p = add('add-language', 'Add a new language')
    add_lang_p.add_argument('code', help='Language code (e.g., de, fr, es)')
    add_lang_p.add_argument('name', help='Language name (e.g., Deutsch, Francais)')

    add('list-languages', 'List all configured languages')

    translate_p = add('translate', 'Create a translation stub for a page')
    translate_p.add_argument('page', help='Page name to translate (e.g., services, about, index)')
    translate_p.add_argument('lang', help='Target language code')

    add('sync-translations', 'Find missing translation keys')

    new_post_p = add('new-post', 'Create a new dated post')
    new_post_p.add_argument('name', help='Post name/slug')
    new_post_p.add_argument('--title', help='Post title')

    add('list-posts', 'List all posts')

    draft_p = add('draft', 'Create a draft page')
    draft_p.add_argument('name', help='Draft name')
    draft_p.add_argument('--title', help='Draft title')

    publish_p = add('publish', 'Publish a draft page')
    publish_p.add_argument('name', help='Draft name to publish')
    publish_p.add_argument('--no-nav', action='store_true', help='Do not add to navigation')

    add('list-drafts', 'List all drafts')
    add('list-taxonomies', 'List all taxonomy terms with post counts')

    add('check', 'Check for missing content files')
    add('validate-yaml', 'Validate all YAML files')
    add('links', 'Check for broken internal links')

    export_parent = _common_parent(suppress=True, with_output=False)
    export_p = sub.add_parser('export', help='Export site source as a ZIP archive',
                              parents=[export_parent])
    export_p.add_argument('--output', '-o', dest='output', help='Output ZIP filename')

    add('status', 'Show site status overview')

    return parser


def _resolve(args):
    positional_site = getattr(args, 'site_name', None)
    named_site = getattr(args, 'site', None)
    if positional_site and named_site and positional_site != named_site:
        raise ValueError(
            f"conflicting site names: positional '{positional_site}' "
            f"and --site '{named_site}'"
        )
    site = positional_site or named_site
    site_dir = resolve_site_dir(
        site_dir=getattr(args, 'site_dir', None),
        site=site,
    )
    config = load_site_config(site_dir)
    output_dir = resolve_output_dir(
        site_dir, output=getattr(args, 'output_dir', None), config=config)
    return site_dir, output_dir, config


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'add-site':
        create_site(args.name, args.title, base_dir=getattr(args, 'dir', None))
        return 0

    debug = getattr(args, 'debug', False)
    configure_logging(debug)

    try:
        return _dispatch(args, debug)
    except ConfigError as exc:
        if debug:
            raise
        print(f"pagesmith: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("pagesmith: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - final guard: no raw tracebacks
        if debug:
            raise
        print(f"pagesmith: error: {exc}", file=sys.stderr)
        return 1


def _dispatch(args, debug):
    try:
        site_dir, output_dir, _config = _resolve(args)
    except (FileNotFoundError, ValueError) as exc:
        if debug:
            raise
        print(f"pagesmith: error: {exc}", file=sys.stderr)
        return 1

    if args.command == 'build':
        builder = SiteBuilder(site_dir, output_dir)
        if builder.build():
            return 0
        if not debug:
            print("pagesmith: build failed (run with --debug for details)",
                  file=sys.stderr)
        return 1

    if args.command == 'serve':
        from .server import serve
        return serve(site_dir, output_dir, host=args.host, port=args.port, debug=debug)

    if args.command == 'watch':
        from .watcher import watch
        return watch(site_dir, output_dir, debug=debug)

    manager = SiteManager(site_dir, output_dir)

    if args.command == 'add-page':
        manager.add_page(args.name, args.title, add_to_nav=not args.no_nav)
    elif args.command == 'remove-page':
        manager.remove_page(args.name, args.keep_files)
    elif args.command == 'list-pages':
        manager.list_pages()

    elif args.command == 'add-language':
        manager.add_language(args.code, args.name)
    elif args.command == 'list-languages':
        manager.list_languages()

    elif args.command == 'translate':
        manager.translate_page(args.page, args.lang)
    elif args.command == 'sync-translations':
        return 0 if manager.sync_translations() else 1

    elif args.command == 'new-post':
        manager.new_post(args.name, args.title)
    elif args.command == 'list-posts':
        manager.list_posts()

    elif args.command == 'draft':
        manager.create_draft(args.name, args.title)
    elif args.command == 'publish':
        manager.publish_draft(args.name, add_to_nav=not args.no_nav)
    elif args.command == 'list-drafts':
        manager.list_drafts()

    elif args.command == 'list-taxonomies':
        manager.list_taxonomies()

    elif args.command == 'check':
        return 0 if manager.check_content() else 1
    elif args.command == 'validate-yaml':
        return 0 if manager.validate_yaml() else 1
    elif args.command == 'links':
        return 0 if manager.check_links() else 1

    elif args.command == 'export':
        manager.export_site(getattr(args, 'output', None))

    elif args.command == 'status':
        manager.show_status()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
