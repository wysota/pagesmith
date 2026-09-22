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
  config/link_schemes.yaml
  content/en/{hero,services,about,skills}.md
  sections/en/{services,about,contact}.md
  translations/en.yaml
  assets/{css/style.css,js/main.js,favicon.svg}
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
(`pip install 'pagesmith[watch]'`).

## 5. Edit content

Homepage sections are plain Markdown:

- `content/en/hero.md` — first non-empty line is the headline, the second is the tagline.
- `content/en/services.md` and `content/en/skills.md` — cards, one per line:

  ```markdown
  - **Card Title**: Card description.
  ```

- `content/en/about.md` — first line is the title, paragraphs become body text,
  and `- ` bullets become an expertise list.

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
pip install -e '.[watch,serve]'
make build              # pagesmith build --site default
make build SITE=test    # pagesmith build --site test
make serve SITE=test
make test
make verify             # build + tests + config/content/link checks
```
