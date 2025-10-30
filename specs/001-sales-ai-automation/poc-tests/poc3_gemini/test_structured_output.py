#!/usr/bin/env python3
"""
POC 3: Gemini JSON Structured Output Quality Test
Tests Gemini 1.5 Flash's ability to consistently generate valid, schema-compliant JSON output.

Success Criteria:
- Schema compliance rate >95%
- Valid JSON rate >99%
- Hallucination rate <5%
- Field completeness >90%

Requirements:
- Google Gemini API key
- Python 3.9+
- google-generativeai package
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import statistics
import re

import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of validating a single JSON output"""
    test_id: str
    input_length: int
    output_length: int
    is_valid_json: bool
    is_schema_compliant: bool
    completeness_score: float
    hallucination_detected: bool
    response_time_ms: float
    error_message: Optional[str] = None
    missing_fields: List[str] = None
    extra_fields: List[str] = None

@dataclass
class TestResults:
    """Overall test results"""
    total_tests: int
    valid_json_count: int
    schema_compliant_count: int
    avg_completeness: float
    hallucination_count: int
    avg_response_time_ms: float
    valid_json_rate: float
    schema_compliance_rate: float
    hallucination_rate: float
    passed: bool
    details: List[ValidationResult]

# Expected schema for Agent 1 (Participant Profile Analyzer)
AGENT1_SCHEMA = {
    "required_fields": [
        "participants",
        "participants[].role",
        "participants[].name",
        "participants[].organizationLevel",
        "participants[].decisionMakingPower"
    ],
    "optional_fields": [
        "participants[].department",
        "participants[].painPoints",
        "participants[].interests"
    ]
}

# Expected schema for Agent 5 (Discovery Questionnaire Analyzer)
AGENT5_SCHEMA = {
    "required_fields": [
        "discoveryQuestionnaires",
        "discoveryQuestionnaires[].topic",
        "discoveryQuestionnaires[].featureCategory",
        "discoveryQuestionnaires[].currentStatus",
        "discoveryQuestionnaires[].hasNeed",
        "discoveryQuestionnaires[].completenessScore"
    ],
    "optional_fields": [
        "discoveryQuestionnaires[].needReasons",
        "discoveryQuestionnaires[].noNeedReasons",
        "discoveryQuestionnaires[].barriers"
    ]
}

class GeminiStructuredOutputTester:
    """Test Gemini structured output quality"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize Gemini API client

        Args:
            api_key: Google Gemini API key
            model_name: Model to use (default: gemini-2.0-flash)
        """
        genai.configure(api_key=api_key)

        # Configure model with JSON mode for structured output
        generation_config = {
            "temperature": 0.1,  # Lower temperature for more consistent output
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",  # Enable JSON mode
        }

        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config
        )
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases with expected ground truth"""
        return [
            {
                "id": "agent1_test1",
                "agent": "Agent 1",
                "prompt": """分析以下銷售會議的與會人員樣貌。請以 JSON 格式回傳。

會議內容：
「大家好，我是張總經理，負責整個餐飲事業部。今天也請到我們的 IT 主管李經理，還有財務部的王協理一起來。
我們現在最大的痛點是尖峰時段人手不足，客人等很久。另外成本控管也需要更精確。」

請以以下格式回傳 JSON：
{
  "participants": [
    {
      "role": "決策者" | "影響者" | "使用者" | "守門人",
      "name": "姓名",
      "organizationLevel": "高階主管" | "中階主管" | "基層員工",
      "decisionMakingPower": "high" | "medium" | "low",
      "department": "部門",
      "painPoints": ["痛點1", "痛點2"],
      "interests": ["關注點1"]
    }
  ]
}""",
                "schema": AGENT1_SCHEMA,
                "ground_truth": {
                    "participants": [
                        {"role": "決策者", "name": "張總經理", "organizationLevel": "高階主管"},
                        {"role": "影響者", "name": "李經理", "department": "IT"},
                        {"role": "影響者", "name": "王協理", "department": "財務"}
                    ]
                }
            },
            {
                "id": "agent5_test1",
                "agent": "Agent 5",
                "prompt": """從以下對話中提取需求問卷資訊。請以 JSON 格式回傳。

對話內容：
「我們有考慮過掃碼點餐，但是客人都是老人家，不太會用手機。不過中午尖峰時段真的很忙，一個人要顧十幾桌。」

請以以下格式回傳 JSON：
{
  "discoveryQuestionnaires": [
    {
      "topic": "功能名稱",
      "featureCategory": "類別",
      "currentStatus": "使用中" | "未使用" | "考慮中" | "曾使用過",
      "hasNeed": true | false | null,
      "needReasons": [{"reason": "原因", "quote": "引文", "confidence": 85}],
      "noNeedReasons": [{"reason": "原因", "quote": "引文", "confidence": 90}],
      "completenessScore": 80
    }
  ]
}""",
                "schema": AGENT5_SCHEMA,
                "ground_truth": {
                    "discoveryQuestionnaires": [
                        {
                            "topic": "掃碼點餐",
                            "currentStatus": "考慮中",
                            "hasNeed": None  # Mixed signals
                        }
                    ]
                }
            },
            {
                "id": "agent1_test2",
                "agent": "Agent 1",
                "prompt": """分析以下銷售會議的與會人員樣貌。請以 JSON 格式回傳。

會議內容：
「我是現場店長阿明，每天都在用 POS 系統。老闆說要找新系統，所以我來看看。我們最需要的是簡單好用，員工訓練不要太久。」

JSON 格式與前例相同。""",
                "schema": AGENT1_SCHEMA,
                "ground_truth": {
                    "participants": [
                        {"role": "使用者", "name": "阿明", "organizationLevel": "基層員工"}
                    ]
                }
            },
            {
                "id": "agent5_test2",
                "agent": "Agent 5",
                "prompt": """從以下對話中提取需求問卷資訊。請以 JSON 格式回傳。

對話內容：
「線上訂位我們已經用了，很方便。外送平台也都有串接 foodpanda 和 Uber Eats。現在想要看看庫存管理，因為常常食材過期浪費掉。」

JSON 格式與前例相同。""",
                "schema": AGENT5_SCHEMA,
                "ground_truth": {
                    "discoveryQuestionnaires": [
                        {"topic": "線上訂位管理", "currentStatus": "使用中"},
                        {"topic": "外送平台整合", "currentStatus": "使用中"},
                        {"topic": "庫存管理", "currentStatus": "考慮中"}
                    ]
                }
            },
            {
                "id": "agent1_hallucination_test",
                "agent": "Agent 1",
                "prompt": """分析以下銷售會議的與會人員樣貌。請以 JSON 格式回傳。

會議內容：
「我是小陳。」

JSON 格式與前例相同。""",
                "schema": AGENT1_SCHEMA,
                "ground_truth": {
                    "participants": [
                        {"name": "小陳"}
                    ]
                },
                "test_hallucination": True  # Should not invent role/level without evidence
            }
        ]

    def validate_json(self, text: str) -> tuple[bool, Optional[dict], Optional[str]]:
        """
        Validate if text is valid JSON and extract it

        Returns:
            (is_valid, parsed_json, error_message)
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)

        try:
            parsed = json.loads(text)
            return True, parsed, None
        except json.JSONDecodeError as e:
            return False, None, str(e)

    def check_schema_compliance(self, data: dict, schema: dict) -> tuple[bool, List[str], float]:
        """
        Check if JSON data complies with expected schema

        Returns:
            (is_compliant, missing_fields, completeness_score)
        """
        missing_fields = []

        # Check required fields
        for field_path in schema["required_fields"]:
            if not self._check_field_exists(data, field_path):
                missing_fields.append(field_path)

        # Calculate completeness (required + optional)
        all_fields = schema["required_fields"] + schema["optional_fields"]
        present_fields = [f for f in all_fields if self._check_field_exists(data, f)]
        completeness = len(present_fields) / len(all_fields) * 100 if all_fields else 0

        is_compliant = len(missing_fields) == 0

        return is_compliant, missing_fields, completeness

    def _check_field_exists(self, data: dict, field_path: str) -> bool:
        """Check if a field path exists in data (supports array notation)"""
        parts = field_path.split('.')

        current = data
        for part in parts:
            if '[]' in part:
                # Array field
                array_key = part.replace('[]', '')
                if array_key not in current or not isinstance(current[array_key], list):
                    return False
                # Check if at least one array element exists
                if len(current[array_key]) == 0:
                    return False
                # Continue checking in first element
                current = current[array_key][0] if current[array_key] else {}
            else:
                if part not in current:
                    return False
                current = current[part]

        return True

    def detect_hallucination(self, test_case: dict, output_data: dict) -> bool:
        """
        Detect if LLM hallucinated information not in input

        Simple heuristic: Check if output contains significantly more details
        than ground truth when input is minimal
        """
        if not test_case.get("test_hallucination"):
            return False

        ground_truth = test_case["ground_truth"]

        # Check participants example
        if "participants" in output_data and "participants" in ground_truth:
            output_p = output_data["participants"][0] if output_data["participants"] else {}
            truth_p = ground_truth["participants"][0] if ground_truth["participants"] else {}

            # If ground truth has minimal info but output has detailed role/level, it's hallucination
            if "role" not in truth_p and "role" in output_p:
                if output_p["role"] in ["決策者", "影響者", "守門人"]:
                    return True  # Hallucinated specific role

            if "organizationLevel" not in truth_p and "organizationLevel" in output_p:
                if output_p["organizationLevel"] in ["高階主管", "中階主管"]:
                    return True  # Hallucinated org level

        return False

    def test_single_case(self, test_case: dict) -> ValidationResult:
        """Test a single case"""
        test_id = test_case["id"]
        logger.info(f"[{test_id}] Testing {test_case['agent']}...")

        start_time = time.time()

        try:
            # Generate response
            response = self.model.generate_content(test_case["prompt"])
            response_time = (time.time() - start_time) * 1000

            output_text = response.text

            # Validate JSON
            is_valid_json, parsed_data, json_error = self.validate_json(output_text)

            if not is_valid_json:
                logger.error(f"[{test_id}] Invalid JSON: {json_error}")
                return ValidationResult(
                    test_id=test_id,
                    input_length=len(test_case["prompt"]),
                    output_length=len(output_text),
                    is_valid_json=False,
                    is_schema_compliant=False,
                    completeness_score=0.0,
                    hallucination_detected=False,
                    response_time_ms=response_time,
                    error_message=json_error
                )

            # Check schema compliance
            is_compliant, missing_fields, completeness = self.check_schema_compliance(
                parsed_data, test_case["schema"]
            )

            # Detect hallucination
            hallucination = self.detect_hallucination(test_case, parsed_data)

            logger.info(f"[{test_id}] Valid JSON: ✅ | Schema: {'✅' if is_compliant else '❌'} | "
                       f"Completeness: {completeness:.0f}% | Hallucination: {'⚠️' if hallucination else '✅'}")

            return ValidationResult(
                test_id=test_id,
                input_length=len(test_case["prompt"]),
                output_length=len(output_text),
                is_valid_json=True,
                is_schema_compliant=is_compliant,
                completeness_score=completeness,
                hallucination_detected=hallucination,
                response_time_ms=response_time,
                missing_fields=missing_fields
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"[{test_id}] Test failed: {e}")
            return ValidationResult(
                test_id=test_id,
                input_length=len(test_case["prompt"]),
                output_length=0,
                is_valid_json=False,
                is_schema_compliant=False,
                completeness_score=0.0,
                hallucination_detected=False,
                response_time_ms=response_time,
                error_message=str(e)
            )

    def run_all_tests(self, iterations_per_case: int = 3) -> TestResults:
        """Run all test cases with multiple iterations"""
        logger.info(f"Starting POC 3: Gemini Structured Output Tests "
                   f"({len(self.test_cases)} cases × {iterations_per_case} iterations)")

        all_results = []

        for test_case in self.test_cases:
            for i in range(iterations_per_case):
                result = self.test_single_case(test_case)
                all_results.append(result)
                time.sleep(1)  # Avoid rate limits

        # Calculate statistics
        total_tests = len(all_results)
        valid_json_count = sum(1 for r in all_results if r.is_valid_json)
        schema_compliant_count = sum(1 for r in all_results if r.is_schema_compliant)
        hallucination_count = sum(1 for r in all_results if r.hallucination_detected)

        valid_json_rate = (valid_json_count / total_tests * 100) if total_tests > 0 else 0
        schema_compliance_rate = (schema_compliant_count / total_tests * 100) if total_tests > 0 else 0
        hallucination_rate = (hallucination_count / total_tests * 100) if total_tests > 0 else 0

        completeness_scores = [r.completeness_score for r in all_results if r.is_valid_json]
        avg_completeness = statistics.mean(completeness_scores) if completeness_scores else 0

        response_times = [r.response_time_ms for r in all_results]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        # Success criteria
        passed = (
            valid_json_rate >= 99 and
            schema_compliance_rate >= 95 and
            hallucination_rate <= 5 and
            avg_completeness >= 90
        )

        return TestResults(
            total_tests=total_tests,
            valid_json_count=valid_json_count,
            schema_compliant_count=schema_compliant_count,
            avg_completeness=avg_completeness,
            hallucination_count=hallucination_count,
            avg_response_time_ms=avg_response_time,
            valid_json_rate=valid_json_rate,
            schema_compliance_rate=schema_compliance_rate,
            hallucination_rate=hallucination_rate,
            passed=passed,
            details=all_results
        )

def print_results(results: TestResults):
    """Print test results"""
    print("\n" + "="*70)
    print("POC 3: Gemini Structured Output Quality Test Results")
    print("="*70)
    print(f"\nTotal Tests: {results.total_tests}")
    print(f"Valid JSON: {results.valid_json_count} ({results.valid_json_rate:.1f}%)")
    print(f"Schema Compliant: {results.schema_compliant_count} ({results.schema_compliance_rate:.1f}%)")
    print(f"Avg Completeness: {results.avg_completeness:.1f}%")
    print(f"Hallucinations: {results.hallucination_count} ({results.hallucination_rate:.1f}%)")
    print(f"Avg Response Time: {results.avg_response_time_ms:.0f}ms")
    print(f"\nSuccess Criteria:")
    print(f"  ✅ Valid JSON > 99%: {'PASS' if results.valid_json_rate >= 99 else 'FAIL'} ({results.valid_json_rate:.1f}%)")
    print(f"  ✅ Schema Compliance > 95%: {'PASS' if results.schema_compliance_rate >= 95 else 'FAIL'} ({results.schema_compliance_rate:.1f}%)")
    print(f"  ✅ Hallucination < 5%: {'PASS' if results.hallucination_rate <= 5 else 'FAIL'} ({results.hallucination_rate:.1f}%)")
    print(f"  ✅ Completeness > 90%: {'PASS' if results.avg_completeness >= 90 else 'FAIL'} ({results.avg_completeness:.1f}%)")
    print(f"\n{'✅ POC 3 PASSED' if results.passed else '❌ POC 3 FAILED'}")
    print("="*70 + "\n")

def save_results(results: TestResults, output_path: str):
    """Save results to JSON file"""
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": results.total_tests,
            "valid_json_count": results.valid_json_count,
            "schema_compliant_count": results.schema_compliant_count,
            "avg_completeness": results.avg_completeness,
            "hallucination_count": results.hallucination_count,
            "avg_response_time_ms": results.avg_response_time_ms,
            "valid_json_rate": results.valid_json_rate,
            "schema_compliance_rate": results.schema_compliance_rate,
            "hallucination_rate": results.hallucination_rate,
            "passed": results.passed
        },
        "details": [asdict(r) for r in results.details]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_path}")

def main():
    """Main test execution"""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logger.error("Missing GEMINI_API_KEY environment variable")
        return

    tester = GeminiStructuredOutputTester(api_key)
    results = tester.run_all_tests(iterations_per_case=3)

    print_results(results)

    output_path = os.path.join(os.path.dirname(__file__), "poc3_results.json")
    save_results(results, output_path)

if __name__ == "__main__":
    main()
