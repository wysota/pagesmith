# Installation

## Requirements

- **Python 3.9+**
- **`uv`** (recommended) or `pip`

`pagesmith` depends on [Jinja2](https://pypi.org/project/Jinja2/),
[PyYAML](https://pypi.org/project/PyYAML/), and
[Markdown](https://pypi.org/project/Markdown/). These are installed automatically.

## Recommended: install with uv

[uv](https://docs.astral.sh/uv/) is the recommended installer. It manages its
own virtual environments, so it works out of the box even on systems with an
externally-managed Python (Debian/Ubuntu, recent Homebrew).

### From PyPI

```bash
uv tool install 'pagesmith[watch,serve]'
```

This installs the `pagesmith` command into an isolated environment managed by
uv (update it later with `uv tool upgrade pagesmith`).

### From a checkout

```bash
git clone <repository-url> pagesmith
cd pagesmith
uv venv .venv
uv pip install -e '.[watch,serve]'
source .venv/bin/activate
```

An editable install (`-e`) lets you change the package source and see the
effect immediately. In the repository, `make install` runs the same steps.

## Alternative: pip in a virtual environment

If you prefer pip, install into a virtual environment first. On distributions
with an externally-managed Python (Debian/Ubuntu, recent Homebrew) this is
required — installing into the system Python fails.

### From PyPI

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install 'pagesmith[watch,serve]'
```

### From a checkout

```bash
git clone <repository-url> pagesmith
cd pagesmith
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[watch,serve]'
```

## Optional extras

| Extra | Adds | Enables |
|---|---|---|
| `watch` | `watchdog` | `pagesmith watch` |
| `serve` | `livereload` | live-reloading `pagesmith serve` |
| `docs` | `mkdocs` | building this documentation |

`pagesmith serve` and `pagesmith watch` still work without their extras: `serve`
falls back to a plain HTTP server, and `watch` reports a clear error if `watchdog`
is missing.

## Optional: Mermaid diagrams

Rendering ` ```mermaid ` blocks to SVG requires the Mermaid CLI, which must be on
your `PATH` as `mmdc`:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

Diagrams are optional. Sites without Mermaid blocks build normally without it.

## Verify the installation

```bash
pagesmith --version
# pagesmith 0.1.0

pagesmith --help
```

If the command is not found, make sure the directory that `uv` (or `pip`)
installs console scripts into is on your `PATH` (normally handled automatically
for an active uv tool environment or virtual environment).

## Upgrading

```bash
uv tool upgrade pagesmith                          # installed with `uv tool install`
uv pip install --upgrade 'pagesmith[watch,serve]'  # inside a uv-managed venv
pip install --upgrade 'pagesmith[watch,serve]'     # inside a pip venv
```
