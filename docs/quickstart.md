# Quick Start

This walkthrough creates a site, builds it, previews it, and makes a first edit.

## 1. Create a site

```bash
pagesmith add-site mysite --title "My Site"
```

This scaffolds a self-contained site in `./mysite/`:

```text
mysite/
  config/site.yaml
  content/en/index.md
  translations/en.yaml
  assets/{css/style.css,favicon.svg}
```

Use `--dir` to create it somewhere else:

```bash
pagesmith add-site mysite --dir ~/sites --title "My Site"
# -> ~/sites/mysite
```

## 2. Build it

```bash
pagesmith build --site-dir mysite
```

With no `--output`, the result is written to `./build/mysite/`. Open
`build/mysite/index.html` in a browser, or pass an explicit destination:

```bash
pagesmith build --site-dir mysite --output /var/www/mysite
```

## 3. Preview with a server

```bash
pagesmith serve --site-dir mysite
# http://0.0.0.0:8000
```

Change the bind address or port:

```bash
pagesmith serve --site-dir mysite --host 127.0.0.1 --port 8080
```

## 4. Rebuild on change

```bash
pagesmith watch --site-dir mysite
```

`watch` performs an initial build, then rebuilds whenever content, config,
translations, or templates change. Requires the `watch` extra
(`uv tool install 'pagesmith[watch]'` or `pip install 'pagesmith[watch]'`).

## 5. Edit content

The homepage is a single Markdown file, `content/en/index.md`:

- The first `# Heading` becomes the page title.
- The rest of the body is rendered into the main content area.

```markdown
# My Site

Anything you like — this is the homepage.
```

To build a homepage from several Markdown files (a hero, cards, an about block…),
see [Composing a page from multiple Markdown files](content.md#composing-a-page-from-multiple-markdown-files),
or study the runnable `sites/hero-example/` site in this repository.

Standalone pages live in `sections/en/`. A page titled `# Services` in
`sections/en/services.md` is published at `sections/services.html`.

See [Writing Content](content.md) for the full picture.

## 6. Common next steps

```bash
# Add a standalone page (also creates its markdown files)
pagesmith add-page portfolio --title "Portfolio" --site-dir mysite

# Add a blog post (dated file under posts/en/)
pagesmith new-post hello-world --title "Hello World" --site-dir mysite

# Add a language
pagesmith add-language de "Deutsch" --site-dir mysite

# Inspect the site
pagesmith status --site-dir mysite
pagesmith list-pages --site-dir mysite
pagesmith list-posts --site-dir mysite
```

## How sites are located

`pagesmith` resolves the site directory in this order:

1. `--site-dir PATH` — a directory containing `config/site.yaml`.
2. `PAGESMITH_SITE_DIR` environment variable.
3. `--site NAME` — tries `./sites/NAME`, then `./NAME`.

Example using the environment variable:

```bash
export PAGESMITH_SITE_DIR=~/sites/mysite
pagesmith build
pagesmith serve
```

## How output is located

The output directory is resolved in this order:

1. `--output DIR` (or `PAGESMITH_OUTPUT`).
2. `build.output_dir` from `config/site.yaml` — absolute, or relative to the
   site root.
3. `./build/<site-name>` in the current working directory.

For safety, `pagesmith` refuses to write output into the site directory, one of
its source subdirectories, or an ancestor of the site.

## Working in this repository

The repository ships example sites under `sites/` and a `Makefile` that wraps the
CLI. `SITE` selects the site (default `default`):

```bash
make install            # uv venv .venv + uv pip install -e '.[watch,serve]'
make build              # pagesmith build --site default
make build SITE=hero-example   # build the hero-composed example site
make build SITE=test    # pagesmith build --site test
make serve SITE=test
make test
make verify             # build + tests + config/content/link checks
```

`sites/default/` is the minimal starter (one homepage file). `sites/hero-example/`
is the classic hero landing page, demonstrating a homepage composed from several
Markdown files plus a per-site `templates/` override and custom assets.
