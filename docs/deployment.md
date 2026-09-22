# Deployment

`pagesmith` produces a directory of static files. Deploy it anywhere that can
serve static content.

## Produce a release build

```bash
pagesmith build --site-dir ~/sites/mysite --output /tmp/mysite-release
```

The output directory contains the default language at the root and other
languages in subdirectories, plus `assets/`, `images/`, `files/`, `feed.xml`, and
`sitemap.xml`.

Always build to a clean directory. `pagesmith` overwrites generated files, but
stale files from a previous layout can linger. Remove the output (or use a fresh
path) before a release build:

```bash
rm -rf /tmp/mysite-release
pagesmith build --site-dir ~/sites/mysite --output /tmp/mysite-release
```

## Verify before publishing

```bash
pagesmith validate-yaml --site-dir ~/sites/mysite
pagesmith check         --site-dir ~/sites/mysite
pagesmith links         --site-dir ~/sites/mysite   # after building
```

Each command exits `1` on failure, so they work in CI. In this repository,
`make verify` runs the build plus all checks.

## Configure absolute URLs

Set `site.base_url` so the feed, sitemap, and any absolute links are correct:

```yaml
site:
  name: "My Site"
  base_url: "https://example.com"
```

The generated pages themselves use **relative** URLs, so the site works under a
subdirectory as well as at a domain root.

## Upload

Copy the output directory to your host. Examples:

```bash
# rsync to a server
rsync -av --delete /tmp/mysite-release/ user@host:/var/www/mysite/

# or a simple static host CLI
aws s3 sync /tmp/mysite-release s3://my-bucket --delete
```

Any static host (GitHub Pages, Netlify, Cloudflare Pages, S3, nginx) works.

## Serving locally

```bash
pagesmith serve --site-dir ~/sites/mysite --port 8080
```

`serve` builds in memory and serves the output over HTTP; it is intended for
previewing, not production.
