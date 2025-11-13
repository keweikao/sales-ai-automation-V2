.PHONY: test-analysis test-agent67 test-slack test-summary-web test-all

test-analysis:
	PYTHONPATH=analysis-service/src pytest analysis-service/tests

test-agent67:
	pytest analysis-service/tests/test_agent67_contract.py
	python3 analysis-service/src/agents/run_agent6_agent7.py --mock-scenario positive --output-dir tmp/agent67_mock

test-slack:
	python3 src/slack_app/test_notifications.py
	pytest src/slack_app/tests

test-summary-web:
	pytest web-service/tests

test-all: test-analysis test-agent67 test-slack test-summary-web
