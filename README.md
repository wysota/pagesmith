# pagesmith — Multi-Language Static Site Generator

A multi-site, multi-language static site generator built with **Python + Jinja2**.
Write content in Markdown with YAML frontmatter, configure a site in YAML, and
`pagesmith` generates fully static HTML pages for every configured language.

The generator is an installable Python package. **Sites are self-contained
directories that can live anywhere on disk** — they are never bundled with the
tool itself.

## Install

```bash
pip install -e '.[watch,serve]'   # from a checkout
pagesmith --version
```

Runtime dependencies (`Jinja2`, `PyYAML`, `Markdown`) are declared in
`pyproject.toml`. Extras add `watchdog` (`watch`) and `livereload` (`serve`).

## Quick Start

```bash
pagesmith add-site mysite --dir . --title "My Site"   # scaffold a site
pagesmith build --site-dir mysite                      # build it
pagesmith serve --site-dir mysite                      # http://0.0.0.0:8000
pagesmith watch --site-dir mysite                      # rebuild on change
pagesmith --help
```

`make` targets wrap the CLI in this repository:

```bash
make test        # Run unit tests (stdlib unittest)
make verify      # test + a scaffold/build smoke check
make docs        # Build the user docs (mkdocs --strict)
make docs-serve  # Serve the docs with live reload
```

## How Sites Are Located

The site directory is resolved in this order:

1. `--site-dir PATH` — a directory containing `config/site.yaml`
2. `PAGESMITH_SITE_DIR` environment variable
3. `--site NAME` — `./sites/NAME` (or `./NAME`) relative to the current directory
   (handy when a site repository keeps multiple sites under `sites/`)

The output directory is resolved in this order:

1. `--output DIR` (or `PAGESMITH_OUTPUT`)
2. `build.output_dir` from `config/site.yaml` (absolute, or relative to the site root)
3. `./build/<site-name>` at the current working directory

Output may be anywhere except the site directory or one of its source subdirectories
(the generator refuses those to protect your source tree).

## CLI Commands

`build`, `serve`, `watch`, `add-site`, `add-page`, `remove-page`, `list-pages`,
`add-language`, `list-languages`, `translate`, `sync-translations`, `new-post`,
`list-posts`, `draft`, `publish`, `list-drafts`, `list-taxonomies`, `check`,
`validate-yaml`, `links`, `export`, `status`.

```bash
pagesmith add-page portfolio --site-dir mysite
pagesmith new-post hello-world --title "Hello World" --site-dir mysite
pagesmith check --site-dir mysite
pagesmith export --site-dir mysite -o backup.zip
```

## Repository Layout

```
pyproject.toml                # Packaging metadata, dependencies, entry point
src/pagesmith/                # The installable package
  cli.py                      # `pagesmith` command dispatch
  builder.py                  # SiteBuilder orchestrator
  manager.py                  # Site management (pages, posts, drafts, export)
  paths.py                    # Site/output path resolution
  server.py watcher.py        # Dev server and file watcher
  templates/                  # Shared Jinja2 templates (base + partials)
  plugins/                    # Python plugins (mermaid, code linking, emoji)
  shortcodes/                 # Built-in shortcode implementations
  scaffold/                   # Files copied into new sites by `add-site`
tests/                        # Unit tests (stdlib unittest)
docs/                         # User documentation (MkDocs)
Makefile                      # Thin wrappers: test, verify, docs
```

## Key Features

- **Multi-language** output with per-language fallback and a language switcher
- **Section pages & child pages** with automatic breadcrumbs and child listings
- **Blog posts & taxonomies** — tags/categories generate index and term pages
- **Shortcodes** — `youtube`, `figure`, `highlight`, `gist`, `emoji`, `data`,
  `download`, `child_link`, `children` (see `src/pagesmith/shortcodes/`)
- **Emoji** — markdown shorthand (`:rocket:`) or the `{% emoji %}` shortcode
- **Mermaid diagrams** — rendered to SVG at build time (requires `@mermaid-js/mermaid-cli` on `PATH`)
- **Code linking** — auto-links C/C++ standard library symbols to cppreference.com
- **RSS/Atom feeds & sitemap** — generated automatically from posts

## Documentation

User documentation lives in `docs/` and is built with
[MkDocs](https://www.mkdocs.org/): overview, installation, quick start, CLI
reference, site structure, configuration, content, translations, templates,
shortcodes, features, deployment, and troubleshooting.

Build or preview it locally:

```bash
pip install '.[docs]'
mkdocs serve     # preview at http://127.0.0.1:8000
mkdocs build     # write the site to ./site/
```

## Development

```bash
pip install -e .
make test        # Run unit tests (stdlib unittest)
make verify      # test + scaffold/build smoke check
```

The test suite is self-contained: integration tests scaffold throwaway sites in
temporary directories, so no sample site ships with the package.