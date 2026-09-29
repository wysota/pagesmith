# Configuration

## `site.yaml`

Every site has `config/site.yaml`. A complete example:

!!! note "Required vs. defaulted"
    `languages` and `pages` (with an `index` page) are required. The `build`
    section is optional — any missing key falls back to the default listed in
    the table below. A malformed or incomplete config is reported as a clear
    `pagesmith: error: ...` message; run with `--debug` to see the traceback.


```yaml
site:
  name: "My Site"
  base_url: "https://example.com"

languages:
  en:
    name: "English"
    code: "en"
    default: true
  pl:
    name: "Polski"
    code: "pl"
    default: false

build:
  content_dir: "content"
  sections_dir: "sections"
  images_dir: "images"
  permalink: "posts/:slug"
  paginate: true
  posts_per_page: 5

taxonomies:
  tags:
    singular: "tag"
    plural: "tags"
    slug: "tags"
    enabled: true
  categories:
    singular: "category"
    plural: "categories"
    slug: "categories"
    enabled: true

pages:
  index:
    template: "index.html"
    content_files: [index.md]
```

### `site`

| Key | Required | Description |
|---|---|---|
| `name` | yes | Site name, used in templates (`site.name`). |
| `base_url` | recommended | Canonical base URL, used in feeds and the sitemap. |

### `languages`

A map of language code to settings. Exactly one language should set
`default: true`; if none does, the first entry is used.

| Key | Description |
|---|---|
| `name` | Human-readable name (language switcher, logs). |
| `code` | The language code (should match the map key). |
| `default` | `true` for the default language (output at the root). |

The default language is written to the output root (`index.html`,
`sections/...`); other languages go into a subdirectory (`pl/index.html`,
`pl/sections/...`).

### `build`

| Key | Default | Description |
|---|---|---|
| `output_dir` | *(unset)* | Where to write output. Absolute, or relative to the site root. When unset, `./build/<site-name>` is used. |
| `content_dir` | `content` | Homepage section sources. |
| `sections_dir` | `sections` | Standalone page sources. |
| `images_dir` | `images` | Image sources copied to the output. |
| `permalink` | `posts/:slug` | Post URL pattern. Supports `:slug`, `:year`, `:month`, `:day`. |
| `paginate` | `true` | Split the blog archive into pages. |
| `posts_per_page` | `5` | Posts per archive page. |

!!! tip "Keep output out of the source tree"
    Output is rejected if it equals the site directory, one of its source
    subdirectories, or an ancestor of the site. Prefer an external path.

### `taxonomies`

Each entry defines a taxonomy generated from post/page frontmatter.

| Key | Description |
|---|---|
| `singular` | Singular label. |
| `plural` | Plural label (used in index headings). |
| `slug` | URL segment (`tags` → `tags/index.html`, `tags/<term>/index.html`). |
| `enabled` | Set `false` to skip this taxonomy. |

The default `tags` and `categories` are enabled automatically if the
`taxonomies` block is omitted.

### `pages`

Each key is a page identifier. The `index` page is special; every other page
with `section: true` is a section page.

**Index page**

| Key | Description |
|---|---|
| `template` | Template to render (normally `index.html`). |
| `content_files` | Markdown files composing the homepage from `content/{lang}/` (see [Site Structure](site-structure.md#contentlang) and [Composing a page](content.md#composing-a-page-from-multiple-markdown-files)). |

**Section page**

| Key | Description |
|---|---|
| `template` | Template to render (normally `page.html`). |
| `nav_name` | Navigation label. |
| `markdown` | File name under `sections/{lang}/`. |
| `section` | Must be `true` for the page to be built. |

## `link_schemes.yaml`

Optional. Configures the [code-linking](features.md#code-linking) plugin that
turns identifiers in code blocks into links.

```yaml
linker_options:
  link_class: 'code-link'
  skip_existing_links: true
  verbose: false

link_schemes:
  qt_class:
    enabled: true
    pattern: '\b(?P<name>Q[A-Z]\w+)\b'
    url: 'https://doc.qt.io/qt-6/{name}.html'
    transform:
      name: 'name.lower()'
    description: 'Qt 6 class reference'

cppreference:
  enabled: true
  # cache_dir: '/custom/cache'   # default: ~/.cache/cppreference/
  force_refresh: false
```

| Key | Description |
|---|---|
| `enabled` | Turn the scheme on or off. |
| `pattern` | Python regular expression with named groups. |
| `url_type` | `template` (default) or `cppreference`. |
| `url` | URL template using `{group}` placeholders (template type). |
| `transform` | Per-group Python expressions evaluated with the group names as locals. |
| `priority` | Higher numbers are processed first. |
| `description` | Human-readable label. |

`linker_options` applies globally (`link_class`, `skip_existing_links`,
`verbose`). The `cppreference` block enables automatic C/C++ standard-library
linking via downloaded indices.

## Environment variables

| Variable | Effect |
|---|---|
| `PAGESMITH_SITE_DIR` | Default site directory when `--site-dir` is not given. |
| `PAGESMITH_OUTPUT` | Default output directory when `--output` is not given. |

## Validating configuration

```bash
pagesmith validate-yaml --site-dir mysite
pagesmith check --site-dir mysite
```
