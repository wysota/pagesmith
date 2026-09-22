"""Path resolution helpers for site and output directories.

Resolution rules
----------------
Site directory:
    ``--site-dir``  >  ``PAGESMITH_SITE_DIR``  >  ``--site`` (cwd ``sites/<name>``
    or ``cwd/<name>``). Sites are never resolved inside the site directory of the
    installed package — each site is a self-contained directory.

Output directory:
    ``--output``  >  ``PAGESMITH_OUTPUT``  >  ``site.yaml build.output_dir``
    (absolute, or relative to the site root)  >  ``./build/<site-name>`` at cwd.
"""

import copy
import os
from pathlib import Path
from typing import Optional

import yaml

ENV_SITE_DIR = "PAGESMITH_SITE_DIR"
ENV_OUTPUT = "PAGESMITH_OUTPUT"
DEFAULT_SITE = "default"


class ConfigError(ValueError):
    """Raised when ``site.yaml`` is malformed or missing required data."""


#: Default values applied when the ``build`` section is missing or partial.
DEFAULT_BUILD = {
    "content_dir": "content",
    "sections_dir": "sections",
    "images_dir": "images",
    "permalink": "posts/:slug",
    "paginate": True,
    "posts_per_page": 5,
}

#: Taxonomy definitions used when the ``taxonomies`` section is omitted.
DEFAULT_TAXONOMIES = {
    "tags": {
        "singular": "tag",
        "plural": "tags",
        "slug": "tags",
        "enabled": True,
    },
    "categories": {
        "singular": "category",
        "plural": "categories",
        "slug": "categories",
        "enabled": True,
    },
}

# Source subdirectories that must never be used as the output directory.
_SOURCE_SUBDIRS = {
    "content",
    "sections",
    "assets",
    "images",
    "files",
    "data",
    "translations",
    "config",
    "templates",
}


def package_dir() -> Path:
    """Return the directory containing the installed ``pagesmith`` package."""
    return Path(__file__).resolve().parent


def package_templates_dir() -> Path:
    """Return the package's shared (framework) templates directory."""
    return package_dir() / "templates"


def builtin_plugins_dir() -> Path:
    """Return the package's built-in plugins directory."""
    return package_dir() / "plugins"


def scaffold_dir() -> Path:
    """Return the directory containing default files for new sites."""
    return package_dir() / "scaffold"


def _normalize_languages(config: dict, config_file: Path) -> None:
    """Validate ``languages`` and make sure exactly one is the default."""
    languages = config.get("languages")
    if not isinstance(languages, dict) or not languages:
        raise ConfigError(
            f"{config_file}: missing required 'languages' section. "
            "Define at least one language, e.g.\n"
            "languages:\n"
            "  en:\n"
            "    name: English\n"
            "    default: true"
        )

    normalized = {}
    for code, settings in languages.items():
        if not isinstance(settings, dict):
            raise ConfigError(
                f"{config_file}: language '{code}' must be a mapping "
                "with a 'name' (and optional 'code')."
            )
        entry = dict(settings)
        entry.setdefault("name", code)
        entry.setdefault("code", code)
        entry["default"] = bool(entry.get("default", False))
        normalized[code] = entry

    if not any(entry["default"] for entry in normalized.values()):
        normalized[next(iter(normalized))]["default"] = True

    config["languages"] = normalized


def _normalize_build(config: dict, config_file: Path) -> None:
    """Fill in the documented ``build`` defaults for missing keys."""
    build = config.get("build")
    if build is None:
        build = {}
    if not isinstance(build, dict):
        raise ConfigError(f"{config_file}: 'build' must be a mapping.")
    merged = copy.deepcopy(DEFAULT_BUILD)
    merged.update(build)
    config["build"] = merged


def _normalize_pages(config: dict, config_file: Path) -> None:
    """Validate that ``pages`` defines the always-built ``index`` page."""
    pages = config.get("pages")
    if not isinstance(pages, dict) or not pages:
        raise ConfigError(
            f"{config_file}: missing required 'pages' section. At minimum, "
            "define the 'index' page, e.g.\n"
            "pages:\n"
            "  index:\n"
            "    template: index.html\n"
            "    content_files: [hero.md, about.md]"
        )
    if "index" not in pages:
        raise ConfigError(
            f"{config_file}: 'pages' must define an 'index' page."
        )
    config["pages"] = pages


def load_site_config(site_dir) -> dict:
    """Load, validate, and normalize ``<site_dir>/config/site.yaml``.

    Missing ``build`` keys fall back to the documented defaults, so a minimal
    config still builds. Clearly invalid or incomplete configs raise
    :class:`ConfigError` with an actionable message instead of failing later
    with a ``KeyError``.
    """
    site_dir = Path(site_dir)
    config_file = site_dir / "config" / "site.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_file}: invalid YAML: {exc}") from exc

    if config is None:
        raise ConfigError(f"{config_file}: configuration is empty.")
    if not isinstance(config, dict):
        raise ConfigError(f"{config_file}: top-level config must be a mapping.")

    site = config.get("site")
    if site is None:
        config["site"] = {"name": site_dir.name, "base_url": ""}
    elif not isinstance(site, dict):
        raise ConfigError(f"{config_file}: 'site' must be a mapping.")
    else:
        site.setdefault("name", site_dir.name)
        site.setdefault("base_url", "")

    _normalize_languages(config, config_file)
    _normalize_build(config, config_file)
    _normalize_pages(config, config_file)

    taxonomies = config.get("taxonomies")
    if taxonomies is None:
        config["taxonomies"] = copy.deepcopy(DEFAULT_TAXONOMIES)
    elif not isinstance(taxonomies, dict):
        raise ConfigError(f"{config_file}: 'taxonomies' must be a mapping.")

    return config


def _is_site_dir(path: Path) -> bool:
    return (path / "config" / "site.yaml").is_file()


def _require_site_dir(path: Path) -> Path:
    if not _is_site_dir(path):
        raise FileNotFoundError(
            f"No site found at {path} (expected {path / 'config' / 'site.yaml'})"
        )
    return path


def resolve_site_dir(site_dir=None, site: Optional[str] = None, cwd=None) -> Path:
    """Resolve the site directory using the documented precedence."""
    cwd = Path(cwd).resolve() if cwd else Path.cwd().resolve()

    if site_dir:
        return _require_site_dir(Path(site_dir).expanduser().resolve())

    env_site = os.environ.get(ENV_SITE_DIR)
    if env_site:
        return _require_site_dir(Path(env_site).expanduser().resolve())

    if site:
        candidates = [cwd / "sites" / site, cwd / site]
        for candidate in candidates:
            candidate = candidate.resolve()
            if _is_site_dir(candidate):
                return candidate
        checked = ", ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            f"Site '{site}' not found. Checked: {checked}. "
            f"Use --site-dir PATH or set {ENV_SITE_DIR}."
        )

    raise SystemExit(
        "No site specified. Use --site-dir PATH, --site NAME, "
        f"or set {ENV_SITE_DIR}."
    )


def _validate_output_dir(site_dir: Path, output_dir: Path) -> None:
    """Refuse output dirs that could destroy the site source tree."""
    if output_dir == site_dir:
        raise ValueError(f"Refusing to use the site directory as output: {output_dir}")
    if output_dir in site_dir.parents:
        raise ValueError(
            f"Refusing to use an ancestor of the site as output: {output_dir}"
        )
    if output_dir.parent == site_dir and output_dir.name in _SOURCE_SUBDIRS:
        raise ValueError(
            f"Refusing to use a source directory as output: {output_dir}"
        )


def resolve_output_dir(
    site_dir, output=None, config: Optional[dict] = None, cwd=None
) -> Path:
    """Resolve the output directory using the documented precedence."""
    site_dir = Path(site_dir).resolve()
    cwd = Path(cwd).resolve() if cwd else Path.cwd().resolve()

    if output is None:
        output = os.environ.get(ENV_OUTPUT)

    if output:
        resolved = Path(output).expanduser()
        if not resolved.is_absolute():
            resolved = cwd / resolved
    else:
        configured = None
        if config is not None:
            configured = config.get("build", {}).get("output_dir")
        if configured:
            resolved = Path(configured).expanduser()
            if not resolved.is_absolute():
                resolved = site_dir / resolved
        else:
            resolved = cwd / "build" / site_dir.name

    resolved = resolved.resolve()
    _validate_output_dir(site_dir, resolved)
    return resolved
