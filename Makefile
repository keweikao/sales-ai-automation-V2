.PHONY: test-analysis test-agent67 test-slack test-summary-web test-code-intelligence test-all benchmark-agent5 benchmark-agent7 build-code-index

test-analysis:
	PYTHONPATH=analysis-service/src pytest analysis-service/tests

test-slack:
	python3 src/slack_app/test_notifications.py
	pytest src/slack_app/tests

test-summary-web:
	pytest web-service/tests

test-code-intelligence:
	pytest tests/code_intelligence -v

test-all: test-analysis test-slack test-summary-web

build-code-index:
	python3 tools/code_intelligence/cli.py build-index --force
