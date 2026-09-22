# Translations

`pagesmith` builds every configured language. The default language is written to
the output root; other languages get a subdirectory.

```text
build/mysite/
├── index.html            # en (default)
├── sections/
├── tags/
└── pl/                   # non-default
    ├── index.html
    ├── sections/
    └── tags/
```

## Configuring languages

Languages are declared in `config/site.yaml`:

```yaml
languages:
  en:
    name: "English"
    code: "en"
    default: true
  pl:
    name: "Polski"
    code: "pl"
    default: false
```

Add one with:

```bash
pagesmith add-language de "Deutsch" --site-dir mysite
```

This updates the config, creates `translations/de.yaml`, and creates
`content/de/` and `sections/de/`.

## Content fallback

Translated content lives in the language subdirectories
(`content/{lang}/`, `sections/{lang}/`, `posts/{lang}/`). If a file is missing
for a language, the default language's file is used automatically. Partial
translations are therefore fine.

## UI strings

Non-content strings (navigation, buttons, taxonomy headings) live in
`translations/{lang}.yaml`:

```yaml
nav:
  home: Home
  services: Services
  about: About
  contact: Contact
  blog: Blog

footer:
  copyright: All rights reserved.

ui:
  get_started: Get Started
  our_services: What We Offer
  about_us: About Us
  technical_expertise: Expertise
  lets_work_together: Get in Touch
  contact_cta: Have a project in mind? Get in touch.
  read_more: Read more
  related_pages: Related Pages
  previous_page: Previous
  next_page: Next
  no_posts: No posts yet.

taxonomy:
  all_tags: All Tags
  all_categories: All Categories
  tagged_with: Posts tagged with
  in_category: Posts in category
  tags: Tags
  categories: Categories
  no_terms: No terms yet.
```

Templates access these as `{{ t.nav.home }}`, `{{ t.ui.get_started }}`, and so
on. Missing keys fall back to the default language's file; if still missing they
render as empty strings.

## Creating translation stubs

Copy the default-language content for a page into a target language:

```bash
pagesmith translate services pl --site-dir mysite
```

The stub is created with a `<!-- TODO: Translate ... -->` header.

## Finding missing keys

```bash
pagesmith sync-translations --site-dir mysite
```

This reports keys present in the default language file but absent from other
languages' files. It exits non-zero if anything is missing.

## Language switcher

The shared `partials/language-switcher.html` renders a link per language using
the `languages` template variable. It is included by the default
`partials/nav.html` and needs no configuration.
