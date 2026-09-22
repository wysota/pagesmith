# Site Structure

A **site** is a directory containing a `config/site.yaml`. Everything else is
relative to it, and nothing refers back into the installed package.

```text
mysite/
├── config/
│   ├── site.yaml            # Required: languages, pages, build settings
│   └── link_schemes.yaml    # Optional: code-linking rules
├── content/{lang}/          # Homepage sections (hero, services, about, skills)
├── sections/{lang}/         # Standalone pages; subdirectories become child pages
├── posts/{lang}/            # Dated blog posts (YYYY-MM-DD-slug.md)
├── drafts/{lang}/           # Draft pages (never built; created by `draft`)
├── translations/{lang}.yaml # UI strings per language
├── data/                    # Optional YAML data, exposed to templates as `data.*`
├── templates/               # Optional template overrides (win over package templates)
├── assets/                  # CSS/JS/favicon, copied to output (CSS is minified)
├── images/                  # Images, copied to output
├── files/                   # Downloadable files, copied to output
└── diagrams/                # Mermaid sources (.mmd) and render cache
```

## `config/`

- **`site.yaml`** — the only required file. Defines the site name, languages,
  build paths, pages, and taxonomies. See [Configuration](configuration.md).
- **`link_schemes.yaml`** — optional rules for the code-linking plugin. See
  [Configuration](configuration.md#link_schemesyaml) and [Features](features.md#code-linking).

## `content/{lang}/`

Homepage section files consumed by the `index` page. The shared template reads
four files:

| File | Used for |
|---|---|
| `hero.md` | Headline (first line) and tagline (second line) |
| `services.md` | "What we offer" cards |
| `about.md` | About paragraph(s) and an expertise list |
| `skills.md` | Expertise cards |

Cards use one line per card:

```markdown
- **Card Title**: Card description.
```

## `sections/{lang}/`

Standalone pages declared under `pages:` in `site.yaml` with `section: true`.
Each page's `markdown:` value names the file in this directory.

Nested directories create **child pages**:

```text
sections/en/design_patterns.md
sections/en/design_patterns/observer.md
sections/en/design_patterns/visitor.md
sections/en/design_patterns/visitor/python.md   # grandchild
```

Child pages are published beneath the parent (`sections/design_patterns/observer.html`),
get breadcrumbs automatically, and can be listed with the `children` shortcode.

## `posts/{lang}/`

Blog posts, one file per post, named `YYYY-MM-DD-slug.md`. The date prefix and
`slug` drive the permalink (`build.permalink`, default `posts/:slug`). Posts are
paginated (see `build.paginate` / `build.posts_per_page`) and can carry
`tags`/`categories` that generate taxonomy pages.

## `drafts/{lang}/`

Work-in-progress pages. Drafts are ignored by the build. `pagesmith draft`
creates them; `pagesmith publish` moves one into `sections/` and registers it.

## `translations/{lang}.yaml`

UI strings (navigation labels, buttons, taxonomy headings) for one language.
Missing keys fall back to the default language. See [Translations](translations.md).

## `data/`

Optional YAML/JSON-free data files. Each `data/foo.yaml` is available to templates
as `data.foo` and to the `data` shortcode as `data 'foo.bar'`.

## `templates/`

Optional per-site Jinja2 template overrides. A file here with the same path as a
package template takes precedence. See [Templates](templates.md).

## `assets/`, `images/`, `files/`

Copied verbatim into the output (`assets/css/*.css` is minified on copy).
Reference them from templates with the generated URL variables:

```jinja
<link rel="stylesheet" href="{{ urls.assets }}/css/style.css">
<img src="{{ urls.images }}/photo.png" alt="">
<a href="{{ urls.files }}/guide.pdf">Download</a>
```

## `diagrams/`

Mermaid source files (`.mmd`) and the render cache. Generated SVG diagrams are
written to `images/`. See [Features](features.md#mermaid-diagrams).

## Output is separate

Generated HTML never lands inside the source tree unless you explicitly configure
it. By default it goes to `./build/<site-name>`; use `--output` or
`PAGESMITH_OUTPUT` to place it elsewhere.
