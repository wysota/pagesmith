# Troubleshooting

## Common problems

| Symptom | Cause / fix |
|---|---|
| `Site 'x' not found` | Pass `--site-dir PATH`, set `PAGESMITH_SITE_DIR`, or create the site with `pagesmith add-site`. |
| `Config file not found: .../config/site.yaml` | The directory is not a site, or the config was renamed. |
| `missing required 'languages'/'pages' section` | Add the named section to `config/site.yaml`; `index` under `pages` is always required. |
| Missing `build` section | Optional: the documented `build` defaults (`content_dir`, `sections_dir`, `images_dir`, `permalink`, `paginate`, `posts_per_page`) are applied automatically. |
| `Refusing to use the site directory as output` | Choose an output outside the site and its source subdirectories. |
| `mmdc not found` | Install `@mermaid-js/mermaid-cli` globally so `mmdc` is on `PATH`, or remove Mermaid blocks. |
| Page missing from the build | Check `section: true` in `site.yaml` and that `draft` is not `true`. |
| Page not updating | Rebuild (`pagesmith build`). With `serve`/`watch`, wait for the rebuild to finish. |
| Broken internal links | Run `pagesmith links --site-dir <site>` after a build. |
| YAML error | Run `pagesmith validate-yaml --site-dir <site>` and fix the reported file. |
| Missing translations | Run `pagesmith sync-translations --site-dir <site>`. |
| New page has no nav link | Add it to the `items:` list in your site's `data/nav.yaml` (see [Templates](templates.md#data-driven-lists-navigation-menus-link-lists)). |
| Card not appearing on the homepage | Cards must be exactly `- **Title**: Description` in `content/{lang}/*.md`. |
| `UndefinedError` in a template | A referenced translation key or variable is missing; add it to `translations/{lang}.yaml` or guard with `{% if %}`. |
| Taxonomy pages not generated | Posts need `tags`/`categories` frontmatter and must not be drafts. |
| `watch` says watchdog is required | `pip install 'pagesmith[watch]'`. |
| Live reload not working | `pip install 'pagesmith[serve]'`; otherwise `serve` falls back to a plain server. |

## Inspecting a site

```bash
pagesmith status --site-dir mysite          # languages, pages, drafts, posts
pagesmith list-pages --site-dir mysite
pagesmith list-posts --site-dir mysite
pagesmith list-drafts --site-dir mysite
pagesmith list-languages --site-dir mysite
pagesmith list-taxonomies --site-dir mysite
```

## Getting more detail

Failures are reported as succinct `pagesmith: error: ...` messages (no Python
traceback). For the full traceback and verbose logging, run with `--debug`:

```bash
pagesmith --debug build --site-dir mysite
```

## Rebuilding from scratch

Generated output is disposable. Delete it and rebuild:

```bash
rm -rf build/mysite
pagesmith build --site-dir mysite
```

The Mermaid cache can also be cleared safely by deleting
`diagrams/.mermaid_cache.json` in the site.

## Documentation build

To build this documentation locally:

```bash
pip install 'pagesmith[docs]'
mkdocs serve     # live preview at http://127.0.0.1:8000
mkdocs build     # writes ./site/
```
