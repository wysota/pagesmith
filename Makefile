SITE ?= default
PAGESMITH ?= $(if $(wildcard .venv/bin/pagesmith),.venv/bin/pagesmith,pagesmith)

.PHONY: help install build serve watch test verify docs docs-serve clean

help:
	@echo "pagesmith development"
	@echo ""
	@echo "  make install      - Create .venv and install pagesmith with uv (editable, watch+serve)"
	@echo "  make build        - Build site '$(SITE)' to ./build/$(SITE)  (SITE=<name> to change)"
	@echo "  make serve        - Serve site '$(SITE)' locally (http://0.0.0.0:8000)"
	@echo "  make watch        - Rebuild site '$(SITE)' automatically on file changes"
	@echo "  make test         - Run unit tests (unittest discovery)"
	@echo "  make verify       - Run tests and a scaffold/build smoke check"
	@echo "  make docs         - Build docs to ./site (mkdocs --strict)"
	@echo "  make docs-serve   - Serve docs with live reload"
	@echo "  make clean        - Remove build artifacts"
	@echo ""

install:
	@uv venv .venv
	@uv pip install -e '.[watch,serve]'
	@echo "Installed pagesmith into .venv — activate it with: source .venv/bin/activate"

build:
	@$(PAGESMITH) build --site $(SITE)

serve:
	@$(PAGESMITH) serve --site $(SITE)

watch:
	@$(PAGESMITH) watch --site $(SITE)

test:
	@echo "Running unit tests..."
	@PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v

verify: test
	@echo "Scaffolding a throwaway site and building it..."
	@tmpdir=$$(mktemp -d); \
	$(PAGESMITH) add-site smoke --dir "$$tmpdir" --title "Smoke" >/dev/null; \
	$(PAGESMITH) build --site-dir "$$tmpdir/smoke" >/dev/null && \
	echo "✓ Smoke build passed"; \
	rm -rf "$$tmpdir"

docs:
	@echo "Building documentation (requires: uv pip install '.[docs]')..."
	@mkdocs build --strict

docs-serve:
	@echo "Serving documentation (requires: uv pip install '.[docs]')..."
	@mkdocs serve

clean:
	@rm -rf build/ dist/ site/ *.egg-info .pytest_cache
	@echo "Cleaned build artifacts."