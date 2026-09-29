# CLI Reference

The single entry point is the `pagesmith` command. The general shape is:

```bash
pagesmith [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

## Global options

| Option | Environment variable | Description |
|---|---|---|
| `--site NAME` | — | Look up a site at `./sites/NAME` (or `./NAME`), then the repository's `sites/NAME`. |
| `--site-dir PATH` | `PAGESMITH_SITE_DIR` | Point directly at a site directory containing `config/site.yaml`. |
| `--output DIR` | `PAGESMITH_OUTPUT` | Write generated output to `DIR`. |
| `--debug` | — | Enable verbose (debug) logging. |
| `--version` | — | Print the version and exit. |
| `-h`, `--help` | — | Show help. |

Site-wide options may be given **before or after** the command:

```bash
pagesmith --site-dir mysite build
pagesmith build --site-dir mysite
```

`build`, `serve`, and `watch` also accept the site name as a trailing
positional argument, as a shorthand for `--site`:

```bash
pagesmith build mysite          # same as: pagesmith build --site mysite
```

`add-site` does not need site resolution (it creates the site), so it ignores
`--site`/`--site-dir` and uses its own `--dir`.

!!! note "`export` and `--output`"
    The `export` command reuses `-o` / `--output` for the **ZIP filename**, not
    for an output directory.

## Build and preview

### `build`

Build all pages for the site.

```bash
pagesmith build --site-dir mysite
pagesmith build --site default --output /tmp/out
```

### `serve`

Serve the generated output over HTTP. Output is rebuilt by the watcher in
live-reload mode when `livereload` is installed.

```bash
pagesmith serve --site-dir mysite
pagesmith serve --site-dir mysite --host 127.0.0.1 --port 8080
```

| Option | Default |
|---|---|
| `--host` | `0.0.0.0` |
| `--port` | `8000` |

In live-reload mode the dev server also answers `GET`/`HEAD /health` with
`200 OK` (body `ok`), which is handy for uptime monitors, proxy health
checks, or CI that waits on the server to come up — no real `health` file
is needed in the site output.

### `watch`

Build once, then rebuild on file changes (content, sections, posts, config,
translations, templates).

```bash
pagesmith watch --site-dir mysite
```

Requires the `watch` extra (`watchdog`).

## Creating a site

### `add-site`

```bash
pagesmith add-site NAME [--title TITLE] [--dir PARENT]
```

Creates `PARENT/NAME` (default `./NAME`) with config, content, translations, and
starter assets.

```bash
pagesmith add-site mysite --title "My Site"
pagesmith add-site mysite --dir ~/sites --title "My Site"
```

## Page management

### `add-page`

Add a section page to the config and create its markdown file for every language.

```bash
pagesmith add-page NAME [--title TITLE] [--no-nav] --site-dir mysite
```

### `remove-page`

Remove a section page from the config (and its markdown unless `--keep-files`).

```bash
pagesmith remove-page NAME [--keep-files] --site-dir mysite
```

### `list-pages`

```bash
pagesmith list-pages --site-dir mysite
```

!!! tip
    Adding a page does not automatically add it to the navigation. Add an entry
    to the `items:` list in your site's `data/nav.yaml` (navigation is
    data-driven; see [Templates](templates.md#data-driven-lists-navigation-menus-link-lists)).

## Language management

### `add-language`

Add a language to the config and create its content directories and translation
file.

```bash
pagesmith add-language CODE NAME --site-dir mysite
pagesmith add-language de "Deutsch" --site-dir mysite
```

### `list-languages`

```bash
pagesmith list-languages --site-dir mysite
```

## Translation management

### `translate`

Create a translation stub for a page by copying the default-language content.

```bash
pagesmith translate PAGE LANG --site-dir mysite
pagesmith translate services pl --site-dir mysite
```

### `sync-translations`

Report translation keys that exist in the default language but are missing in
other languages.

```bash
pagesmith sync-translations --site-dir mysite
```

## Posts (blog / news)

### `new-post`

Create a dated post `posts/{lang}/YYYY-MM-DD-slug.md` for every language.

```bash
pagesmith new-post NAME [--title TITLE] --site-dir mysite
```

### `list-posts`

```bash
pagesmith list-posts --site-dir mysite
```

### `list-taxonomies`

List taxonomy terms and how many posts use them.

```bash
pagesmith list-taxonomies --site-dir mysite
```

## Drafts

### `draft`

Create an unpublished page under `drafts/{lang}/`.

```bash
pagesmith draft NAME [--title TITLE] --site-dir mysite
```

### `publish`

Move a draft into `sections/` and register it in the config.

```bash
pagesmith publish NAME [--no-nav] --site-dir mysite
```

### `list-drafts`

```bash
pagesmith list-drafts --site-dir mysite
```

## Validation

### `check`

Verify that every content file referenced by the config exists.

```bash
pagesmith check --site-dir mysite
```

### `validate-yaml`

Validate all YAML files under `config/`, `translations/`, and `data/` (including
the data-driven navigation document `data/nav.yaml`).

```bash
pagesmith validate-yaml --site-dir mysite
```

### `links`

Check generated HTML for broken internal links. Build first.

```bash
pagesmith links --site-dir mysite
```

All three exit with status `1` when they find a problem, which makes them
suitable for CI.

## Export and status

### `export`

Archive the site source (config, content, templates, translations, assets) as a
ZIP, excluding generated output and caches.

```bash
pagesmith export --site-dir mysite
pagesmith export --site-dir mysite -o backup.zip
```

### `status`

Show languages, pages, drafts, and posts, then run the content check.

```bash
pagesmith status --site-dir mysite
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success, or a check that passed. |
| `1` | Error (bad site path, invalid config, failed check or build). |

## Makefile shortcuts (this repository)

The `Makefile` wraps the CLI for the bundled example sites. `SITE=name` defaults
to `default`.

```bash
make install                # uv venv .venv + editable install (watch, serve)
make build [SITE=name]      make test
make serve [SITE=name]      make verify
make watch [SITE=name]      make docs | docs-serve | clean
```

`make verify` runs the unit tests plus a throwaway scaffold/build smoke check;
use `pagesmith validate-yaml`, `check`, and `links` directly for the finer-grained
checks.
