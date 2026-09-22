PAGESMITH ?= pagesmith

.PHONY: help test verify docs docs-serve clean

help:
	@echo "pagesmith development"
	@echo ""
	@echo "  make test        - Run unit tests (unittest discovery)"
	@echo "  make verify      - Run tests and a scaffold/build smoke check"
	@echo "  make docs        - Build docs to ./site (mkdocs --strict)"
	@echo "  make docs-serve  - Serve docs with live reload"
	@echo "  make clean       - Remove build artifacts"
	@echo ""

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
	@echo "Building documentation (requires: pip install '.[docs]')..."
	@mkdocs build --strict

docs-serve:
	@echo "Serving documentation (requires: pip install '.[docs]')..."
	@mkdocs serve

clean:
	@rm -rf build/ dist/ site/ *.egg-info .pytest_cache
	@echo "Cleaned build artifacts."