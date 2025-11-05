.PHONY: test-agent67

test-agent67:
	pytest analysis-service/tests/test_agent67_contract.py
	python analysis-service/src/agents/run_agent6_agent7.py --mock-scenario positive --output-dir tmp/agent67_mock
