# Installation

## Requirements

- **Python 3.9+**
- `pip`

`pagesmith` depends on [Jinja2](https://pypi.org/project/Jinja2/),
[PyYAML](https://pypi.org/project/PyYAML/), and
[Markdown](https://pypi.org/project/Markdown/). These are installed automatically.

## Install the package

### From PyPI

```bash
pip install pagesmith
```

With the optional development extras:

```bash
pip install 'pagesmith[watch,serve]'
```

### From a checkout

```bash
git clone <repository-url> pagesmith
cd pagesmith
pip install -e .
```

An editable install (`-e`) lets you change the package source and see the
effect immediately.

### Optional extras

| Extra | Adds | Enables |
|---|---|---|
| `watch` | `watchdog` | `pagesmith watch` |
| `serve` | `livereload` | live-reloading `pagesmith serve` |
| `docs` | `mkdocs` | building this documentation |

`pagesmith serve` and `pagesmith watch` still work without their extras: `serve`
falls back to a plain HTTP server, and `watch` reports a clear error if `watchdog`
is missing.

## Recommended: use a virtual environment

On distributions with an externally-managed Python (Debian/Ubuntu, recent
Homebrew), install into a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install pagesmith
```

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

If the command is not found, make sure the directory that `pip` installs
console scripts into is on your `PATH` (normally handled automatically inside an
activated virtual environment).

## Upgrading

```bash
pip install --upgrade pagesmith
```
