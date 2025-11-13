.PHONY: test-analysis test-agent67 test-slack test-summary-web test-all benchmark-agent5 benchmark-agent7

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

benchmark-agent5:
	PYTHONPATH=analysis-service/src python3 analysis-service/src/agents/benchmark_agent5.py --mock-scenario positive --output-dir tmp/agent5_benchmark

benchmark-agent7:
	PYTHONPATH=analysis-service/src python3 analysis-service/src/agents/run_agent6_agent7.py --agents 7 --mock-scenario positive --output-dir tmp/agent7_benchmark
