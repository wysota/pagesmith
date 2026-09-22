# Templates

Themes are ordinary [Jinja2](https://jinja.palletsprojects.com/) HTML templates.

## Lookup order

Templates are resolved from two locations, **site first**:

1. `<site>/templates/` — your overrides.
2. The package's shared templates (`pagesmith/templates/`).

A file in the site with the same relative path replaces the shared one. To
customise a template, copy it from the package into `<site>/templates/` and edit.

Shared templates:

```text
templates/
├── base.html               # Layout: <head>, nav, footer, theme toggle
├── index.html              # Homepage
├── page.html               # Section and child pages
├── post.html               # A single blog post
├── blog.html               # Paginated post archive
├── taxonomy_index.html     # Tags/categories index
├── taxonomy_term.html      # Posts for one term
└── partials/
    ├── nav.html
    ├── footer.html
    ├── language-switcher.html
    ├── service-card.html
    ├── skill-item.html
    └── children.html
```

`base.html` defines a `title` block, a `head` block, and a `content` block.

## Standard context

Every template receives:

| Variable | Description |
|---|---|
| `t` | UI strings for the current language (`t.nav.home`, `t.ui.*`, `t.taxonomy.*`). |
| `data` | Contents of `data/*.yaml`, keyed by file stem. |
| `urls` | Relative URLs: `urls.home`, `urls.<page>`, `urls.tags`, `urls.categories`, `urls.blog`, `urls.assets`, `urls.images`, `urls.files`. |
| `languages` | List for the language switcher (`code`, `name`, `page_url`). |
| `lang` | Current language (`code`, `name`). |
| `site` | The `site` block from `site.yaml` (`site.name`, `site.base_url`). |
| `current_page` | Page identifier (for active nav state). |
| `year` | Current build year (footer). |

## Page context

Rendered pages add:

| Variable | Available to | Description |
|---|---|---|
| `page` | index, page, post, blog, taxonomy | `title`, `subtitle`, `content`, `description`, `keywords`, plus `parent`/`show_related_pages` where relevant. |
| `metadata` | page, post | Raw frontmatter dict (custom fields). |
| `children` | page | Child pages (`title`, `url`, `order`). |
| `breadcrumbs` | child pages | List of `{title, url}` (last has `url: null`). |
| `posts` | blog, taxonomy term | Post summaries (`title`, `url`, `date`, `author`, `excerpt`). |
| `pagination` | blog | `current_page`, `total_pages`, `has_prev`, `has_next`, `prev_url`, `next_url`. |
| `taxonomy` / `term` | taxonomy pages | Terms and the current term. |

## Filters

| Filter | Example | Result |
|---|---|---|
| `safe` | `{{ page.content \| safe }}` | Output HTML without escaping. |
| `slugify` | `{{ "Hello World" \| slugify }}` | `hello-world` |
| `markdown` | `{{ "**bold**" \| markdown }}` | Inline Markdown to HTML. |

## Example

```jinja
{% extends "base.html" %}

{% block title %}{{ page.title }}{% endblock %}

{% block content %}
<h1>{{ page.title }}</h1>
{% if page.subtitle %}<p class="subtitle">{{ page.subtitle | safe }}</p>{% endif %}
<article>{{ page.content | safe }}</article>

{% if children %}
<ul>
  {% for child in children %}
  <li><a href="{{ child.url }}">{{ child.title }}</a></li>
  {% endfor %}
</ul>
{% endif %}
{% endblock %}
```

## Data-driven lists (navigation, menus, link lists)

The navigation is generated from a data document, not hardcoded in the
template. This is the pattern to reuse for any repeated list (menus, footer
links, sidebars, ...): **define the items in a `data/*.yaml` document, loop over
them in a list template, and render each entry with an item partial.**

The nav uses three pieces:

1. **Data document** — `<site>/data/nav.yaml`. A top-level `items:` list; each
   entry's `name` is the URL key (also used for the default label and the active
   state). The optional `label` is a dot-path into the translations dict and
   overrides the default `t.nav.<name>` label:

   ```yaml
   items:
     - name: home
     - name: design_patterns
     - name: tags
       label: taxonomy.tags
   ```

2. **List template** — `partials/nav.html` loops over the document and includes
   the item partial per entry:

   ```jinja
   {% if data.nav %}
     {% for item in data.nav.get('items', []) %}
       {% include "partials/nav-item.html" %}
     {% endfor %}
   {% endif %}
   ```

3. **Item partial** — `partials/nav-item.html` renders one entry: the URL comes
   from `urls[item.name]`, the active state from `current_page == item.name`
   (the home item is also active on `index` pages), and the label from either
   `item.label` (resolved into `t`, so `taxonomy.tags` works) or `t.nav[item.name]`:

   ```jinja
   <li><a href="{{ urls[item.name] }}"
       {% if current_page == item.name or (item.name == 'home' and current_page == 'index') %}
       class="active"{% endif %}>{{ t.nav[item.name] }}</a></li>
   ```

The same shape works for any list: put the items in a YAML file, expose them
under the `data` context variable, and write a loop template plus an item
partial. The URL/label/active logic can be adjusted per use — the important
part is that the *list itself* lives in a document, so adding/removing/reordering
entries never requires editing a template.

## Overriding the navigation

To customise the nav for one site, override one of its pieces:

- **Change what is shown**: edit `<site>/data/nav.yaml` (add/remove/reorder
  `items:`, set `label:` overrides). No template edits needed.
- **Change how items look**: create `<site>/templates/partials/nav-item.html`
  (overrides the package partial; see the lookup order above).
- **Change the whole nav layout**: copy `partials/nav.html` from the package
  into `<site>/templates/partials/nav.html` and edit. Use `urls.<page>` for
  links and `current_page` for the active state, and keep the `data.nav` loop
  so the list stays data-driven.
