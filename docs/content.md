# Writing Content

All content is Markdown. Depending on where a file lives, it fills a different
role: homepage sections, standalone pages, child pages, or dated posts.

## Page frontmatter

Any Markdown file may begin with YAML frontmatter delimited by `---` lines:

```markdown
---
title: Contact
subtitle: Get in touch
description: How to reach us
keywords: contact, support, email
author: Jane Doe
date: 2026-05-09
draft: false
---

# Contact

Body text...
```

| Field | Type | Purpose |
|---|---|---|
| `title` | string | Overrides the `# Heading` title. |
| `subtitle` | string | Rendered below the title (inline Markdown allowed). |
| `description` | string | SEO description. |
| `keywords` | string | Comma-separated SEO keywords. |
| `author` | string | Author name (mostly for posts/pages). |
| `date` | `YYYY-MM-DD` | Publication date. |
| `draft` | boolean | `true` excludes the page from the build. |
| `child_order` | number | Sort order for child pages (lower first). |
| `show_related_pages` | boolean | Show the children list on a section page (default `true`). |

Custom fields are allowed and are available to templates as `{{ metadata.field }}`.
The opening `---` must be on line 1; both separators are required. If frontmatter
is absent, the title is taken from the first `# Heading` line.

## Homepage sections

The `index` page reads four files from `content/{lang}/`:

**`hero.md`** — title and subtitle only:

```markdown
# My Site
Building great things since 2026.
```

**`services.md` / `skills.md`** — cards, exactly `- **Title**: Description`:

```markdown
- **Consulting**: Architecture reviews and technical guidance.
- **Development**: Building the thing.
```

**`about.md`** — first line is the title, paragraphs become body text, and
bullet items become an expertise list:

```markdown
# About Us

We have been building sites for years.

- Software architecture
- Performance engineering
```

## Standalone pages

A section page is a file in `sections/{lang}/` registered under `pages:` in
`site.yaml`:

```markdown
---
title: Services
subtitle: What we do
---

# Services

We offer the following services...
```

Output path: `sections/<page>.html`.

## Child pages

Put Markdown files in a subdirectory named after the parent page:

```text
sections/en/design_patterns.md
sections/en/design_patterns/observer.md
sections/en/design_patterns/visitor.md
```

- Each child is published at `sections/<parent>/<child>.html`.
- Child pages get **breadcrumbs** automatically.
- Order children with `child_order` frontmatter (default 999).
- List children on the parent (or a child) with the
  [`children` shortcode](shortcodes.md#children).
- Link to a child with the [`child_link` shortcode](shortcodes.md#child_link).

Nesting can go arbitrarily deep (`design_patterns/visitor/python.md`).

## Blog posts

Posts live in `posts/{lang}/` and must be named `YYYY-MM-DD-slug.md`:

```markdown
---
title: "Hello World"
date: 2026-05-09
author: "Jane Doe"
tags: [cplusplus, testing]
categories: [engineering]
---

# Hello World

Content here.

<!--more-->

The rest of the article, hidden from the excerpt.
```

- The URL is built from `build.permalink` (default `posts/:slug`).
- `tags` and `categories` are collected into taxonomy pages.
- `draft: true` skips the post.
- Everything before `<!--more-->` becomes the excerpt; otherwise the first
  paragraph is used.
- Posts are paginated per `build.paginate` and `build.posts_per_page`.

Create posts with:

```bash
pagesmith new-post hello-world --title "Hello World" --site-dir mysite
```

## Drafts

```bash
pagesmith draft new-feature --title "New Feature" --site-dir mysite
# edit drafts/en/new-feature.md
pagesmith publish new-feature --site-dir mysite
```

`publish` moves the files into `sections/` and adds the page to the config. You
still need to add the page to the navigation: add an entry to the `items:` list
in `data/nav.yaml` (see "Navigation" below).

## Adding a page

```bash
pagesmith add-page portfolio --title "Portfolio" --site-dir mysite
```

This registers the page in `site.yaml` and creates `sections/{lang}/portfolio.md`
for every language. Then add it to the navigation and rebuild:

```bash
pagesmith build --site-dir mysite
```

## Navigation

The navigation is **data-driven**: the list of items lives in
`<site>/data/nav.yaml` and the templates render it. Each entry's `name` is the
URL key (also the `current_page` value used for the active state), and the label
defaults to the translation `t.nav.<name>`:

```yaml
items:
  - name: home
  - name: portfolio         # needs: t.nav.portfolio in translations/<lang>.yaml
  - name: tags
    label: taxonomy.tags    # optional label override (dot-path into translations)
```

Add a page to the menu by appending it to the `items:` list — no template edits.
The rendering is split into the list partial `templates/partials/nav.html` and
the per-item partial `templates/partials/nav-item.html`; create site overrides
of either to change the markup. `urls.portfolio` is generated automatically for
every configured section page.
