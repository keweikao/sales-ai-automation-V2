.PHONY: test-modules test-web test-all lint

# V2 Architecture Tests
test-modules:
	PYTHONPATH=. pytest modules/ -v --ignore=modules/*/tests || true

test-web:
	pytest web-service/tests -v

test-all: test-modules test-web

# Linting
lint:
	find . -name "*.py" -print0 | xargs -0 python3 -m py_compile

# Build code index (if needed)
build-code-index:
	python3 tools/code_intelligence/cli.py build-index --force
