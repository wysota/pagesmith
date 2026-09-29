# pagesmith

**pagesmith** is a multi-site, multi-language static site generator built with
Python and [Jinja2](https://jinja.palletsprojects.com/). Write your content in
Markdown with YAML frontmatter, describe the site in a YAML config file, and
`pagesmith` produces a complete static HTML site for every configured language.

The generator is an installable Python package. Each website is a **self-contained
directory** that can live anywhere on disk — it is not tied to the package, and the
generated output can be written to a third location.

```bash
uv tool install 'pagesmith[watch,serve]'
pagesmith add-site mysite --title "My Site"
pagesmith build --site-dir mysite
```

## Highlights

- **Multi-language** output with per-language fallback and a language switcher.
- **Section pages and nested child pages** with automatic breadcrumbs and child listings.
- **Blog posts and taxonomies** — tags and categories generate index and term pages.
- **Shortcodes** — `youtube`, `figure`, `highlight`, `gist`, `emoji`,
  `compiler_explorer`, `data`, `download`, `child_link`, `children`, and `mermaid`.
- **Mermaid diagrams** rendered to SVG at build time.
- **Code linking** of C/C++ symbols to cppreference.com and custom documentation.
- **RSS/Atom feed and sitemap** generated automatically from posts.
- **Template overrides** — a site can override any shared template.

## How it fits together

Three locations, kept independent:

| Thing | Where it lives | Default |
|---|---|---|
| The generator | installed Python package `pagesmith` | `site-packages/pagesmith` |
| Website sources | a site directory with `config/site.yaml` | given by `--site-dir` |
| Generated output | any directory outside the site | `./build/<site-name>` |

## Where to go next

- [Installation](installation.md) — install the package and optional tools.
- [Quick Start](quickstart.md) — create and build your first site.
- [CLI Reference](cli.md) — every command and global option.
- [Site Structure](site-structure.md) — what is inside a site directory.
- [Configuration](configuration.md) — `site.yaml` and `link_schemes.yaml`.
- [Writing Content](content.md) — pages, posts, drafts, and frontmatter.
- [Translations](translations.md) — languages and UI strings.
- [Templates](templates.md) — Jinja2 templates, context, and overrides.
- [Shortcodes](shortcodes.md) — embed media and reuse content.
- [Features](features.md) — diagrams, code linking, emoji, feeds.
- [Deployment](deployment.md) — publish the generated output.
- [Troubleshooting](troubleshooting.md) — common problems and fixes.

## Requirements

- Python 3.9 or newer.
- `Jinja2`, `PyYAML`, and `Markdown` (installed automatically as dependencies).
- Optional: `watchdog` for `pagesmith watch`, `livereload` for `pagesmith serve`.
- Optional: `@mermaid-js/mermaid-cli` (`mmdc` on `PATH`) for Mermaid diagrams.
