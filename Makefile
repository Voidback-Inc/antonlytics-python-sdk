# Antonlytics Python SDK — release helpers.
#
# Quick reference:
#   make build              build wheel + sdist into dist/
#   make publish            upload dist/ to PyPI (uses uv publish)
#   make release            build + publish in one shot
#   make clean              wipe dist/ build/ egg-info/
#
# Auth: set UV_PUBLISH_TOKEN to your PyPI API token (starts with `pypi-`).
#   export UV_PUBLISH_TOKEN=pypi-AgEIcHlw...
# Or pass it inline:
#   make publish UV_PUBLISH_TOKEN=pypi-...
# Get a token at: https://pypi.org/manage/account/token/

.PHONY: build publish release clean version

clean:
	rm -rf dist build *.egg-info

build: clean
	uv build

publish:
	@if [ -z "$$UV_PUBLISH_TOKEN" ]; then \
		echo "error: UV_PUBLISH_TOKEN is not set."; \
		echo "  get a token at https://pypi.org/manage/account/token/"; \
		echo "  then: export UV_PUBLISH_TOKEN=pypi-..."; \
		exit 1; \
	fi
	uv publish

release: build publish
	@VERSION=$$(grep -E '^version' pyproject.toml | head -1 | cut -d'"' -f2); \
	echo "✓ released antonlytics $$VERSION to PyPI"

version:
	@grep -E '^version' pyproject.toml | head -1 | cut -d'"' -f2
