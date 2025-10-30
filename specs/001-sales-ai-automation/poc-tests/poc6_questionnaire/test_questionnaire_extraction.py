#!/usr/bin/env python3
"""
POC 6: Discovery Questionnaire Extraction Accuracy

Tests Agent 5's ability to extract structured questionnaire responses from conversations.

Usage:
    export GEMINI_API_KEY="your-key"
    python test_questionnaire_extraction.py --test-dir ../../test-data/transcripts/
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed. Run: pip install google-generativeai")
    exit(1)


# Ground truth labels for test transcripts
GROUND_TRUTH = {
    "test_01": {
        "features_discussed": [
            {
                "feature": "掃碼點餐",
                "current_status": "未使用",
                "has_need": True,
                "need_reasons": ["尖峰時段人手不足", "點餐效率低"],
                "barriers": ["customer_adoption"],
                "implementation_willingness": "high"
            },
            {
                "feature": "POS點餐系統",
                "current_status": "使用中",
                "has_need": True,
                "need_reasons": ["需要整合掃碼點餐"],
                "barriers": [],
                "implementation_willingness": "high"
            }
        ]
    },
    "test_02": {
        "features_discussed": [
            {
                "feature": "POS點餐系統",
                "current_status": "未使用",
                "has_need": True,
                "need_reasons": ["提升點餐效率", "減少人力成本"],
                "barriers": ["budget"],
                "implementation_willingness": "medium"
            }
        ]
    },
    "test_03": {
        "features_discussed": [
            {
                "feature": "掃碼點餐",
                "current_status": "考慮中",
                "has_need": True,
                "need_reasons": ["自助點餐需求"],
                "barriers": [],
                "implementation_willingness": "high"
            },
            {
                "feature": "線上訂位管理",
                "current_status": "未使用",
                "has_need": True,
                "need_reasons": ["訂位管理混亂"],
                "barriers": [],
                "implementation_willingness": "high"
            },
            {
                "feature": "外送平台整合",
                "current_status": "考慮中",
                "has_need": True,
                "need_reasons": ["外送訂單量增加"],
                "barriers": [],
                "implementation_willingness": "medium"
            }
        ]
    },
    "test_05": {
        "features_discussed": [
            {
                "feature": "線上訂位管理",
                "current_status": "未使用",
                "has_need": True,
                "need_reasons": ["訂位管理需求", "減少電話訂位負擔"],
                "barriers": [],
                "implementation_willingness": "high"
            }
        ]
    },
    "test_06": {
        "features_discussed": [
            {
                "feature": "掃碼點餐",
                "current_status": "未使用",
                "has_need": False,
                "need_reasons": [],
                "barriers": ["tech_resistance", "customer_adoption"],
                "implementation_willingness": "low"
            },
            {
                "feature": "POS點餐系統",
                "current_status": "使用中",
                "has_need": False,
                "need_reasons": [],
                "barriers": ["tech_resistance"],
                "implementation_willingness": "low"
            }
        ]
    },
    "test_07": {
        "features_discussed": [
            {
                "feature": "外送平台整合",
                "current_status": "未使用",
                "has_need": True,
                "need_reasons": ["外送訂單多", "需要整合管理"],
                "barriers": [],
                "implementation_willingness": "high"
            }
        ]
    }
}


AGENT5_PROMPT_TEMPLATE = """# Agent 5: Discovery Questionnaire Analyzer

## Role
You are a sales analyst extracting structured questionnaire responses from sales conversations.

## iCHEF Feature Catalog (22 features, 6 categories)

### 1️⃣ 點餐與訂單管理
1. 掃碼點餐（QR Code 掃碼點餐）
2. 多人掃碼點餐
3. 套餐加價購
4. 智慧菜單推薦
5. POS點餐系統
6. 線上點餐接單

### 2️⃣ 線上整合服務
7. 線上訂位管理
8. 線上外帶自取
9. 雲端餐廳（Online Store）
10. Google整合
11. LINE整合
12. 外送平台整合
13. 聯絡式外帶服務

### 3️⃣ 成本與庫存管理
14. 成本控管
15. 庫存管理
16. 帳款管理

### 4️⃣ 業績與銷售分析
17. 銷售分析
18. 報表生成功能

### 5️⃣ 客戶關係管理
19. 零秒集點（忠誠點數系統 2.0）
20. 會員管理

### 6️⃣ 企業級功能
21. 總部系統
22. 連鎖品牌管理

## Task
For EACH feature mentioned in the conversation (explicitly or implicitly), extract structured questionnaire.

## Output Format (JSON)
Return a JSON object with this EXACT structure:

{{
  "discoveryQuestionnaires": [
    {{
      "topic": "掃碼點餐",
      "featureCategory": "點餐與訂單管理",
      "currentStatus": "使用中" | "未使用" | "考慮中" | "曾使用過",
      "hasNeed": true | false | null,
      "needReasons": [
        {{
          "reason": "尖峰時段人手不足",
          "quote": "客人點餐都要等很久",
          "confidence": 85
        }}
      ],
      "noNeedReasons": [],
      "perceivedValue": {{
        "score": 75,
        "aspects": [
          {{
            "aspect": "省人力",
            "sentiment": "positive"
          }}
        ]
      }},
      "implementationWillingness": "high" | "medium" | "low" | "none",
      "barriers": [
        {{
          "type": "customer_adoption" | "budget" | "tech_resistance" | "integration" | "training",
          "severity": "high" | "medium" | "low",
          "detail": "有些老客人不習慣"
        }}
      ],
      "timeline": {{
        "mentionedTimeline": "一個月內",
        "urgency": "high" | "medium" | "low"
      }},
      "completenessScore": 80,
      "additionalContext": "客戶很有興趣，準備參訪其他餐廳"
    }}
  ]
}}

## Instructions
1. **Topic Detection**: Identify ALL features discussed (even if just mentioned)
2. **Implicit Inference**: Infer status/needs from context
   - Example: "客人不會用手機" → barrier: customer_adoption
   - Example: "尖峰時段很忙" → need_reason: 人手不足
3. **Confidence Scoring**: Assign 0-100 confidence to each extracted reason
   - 90-100: Explicitly stated
   - 70-89: Strong implication
   - 50-69: Weak implication
   - <50: Speculative
4. **Handle Ambiguity**: If unclear, set hasNeed=null and explain in additionalContext
5. **Completeness**: Calculate % of questionnaire fields that were answered

Return ONLY valid JSON. No markdown, no explanation.

---

## Conversation Transcript

{transcript}
"""


class QuestionnaireExtractor:
    """Tests Agent 5 questionnaire extraction accuracy"""

    def __init__(self, api_key: str, model_name="gemini-2.0-flash-exp"):
        genai.configure(api_key=api_key)

        # Configure model for JSON output
        self.model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json"
            }
        )
        self.model_name = model_name

    def extract_questionnaire(self, transcript: str) -> Dict:
        """Extract questionnaire from transcript using Agent 5"""
        prompt = AGENT5_PROMPT_TEMPLATE.format(transcript=transcript)

        start_time = time.time()
        response = self.model.generate_content(prompt)
        duration = time.time() - start_time

        try:
            result = json.loads(response.text)
            return {
                "success": True,
                "result": result,
                "duration": duration,
                "tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {e}",
                "raw_text": response.text[:500],
                "duration": duration
            }


def load_transcript(file_path: str) -> Tuple[str, str]:
    """Load transcript from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    file_id = data.get("fileId", Path(file_path).stem)
    transcript = data.get("text", "")

    return file_id, transcript


def test_topic_detection(test_results: List[Dict], ground_truth: Dict) -> Dict:
    """Test if Agent 5 finds all discussed features"""

    print(f"\n{'='*60}")
    print("TEST 1: TOPIC DETECTION")
    print(f"{'='*60}\n")

    results = {
        "total_features": 0,
        "detected_features": 0,
        "missed_features": [],
        "false_positives": [],
        "recall_scores": []
    }

    for test_result in test_results:
        file_id = test_result["file_id"]

        if file_id not in ground_truth:
            print(f"⚠️  No ground truth for {file_id}, skipping")
            continue

        if not test_result["success"]:
            print(f"❌ {file_id}: Extraction failed")
            continue

        gt = ground_truth[file_id]
        agent_response = test_result["result"]

        detected_topics = {q["topic"] for q in agent_response.get("discoveryQuestionnaires", [])}
        expected_topics = {f["feature"] for f in gt["features_discussed"]}

        results["total_features"] += len(expected_topics)
        detected_count = len(detected_topics & expected_topics)
        results["detected_features"] += detected_count

        recall = detected_count / len(expected_topics) * 100 if expected_topics else 0
        results["recall_scores"].append(recall)

        missed = expected_topics - detected_topics
        false_pos = detected_topics - expected_topics

        status = "✅" if recall == 100 else "⚠️" if recall >= 75 else "❌"
        print(f"{status} {file_id}: {recall:.1f}% recall ({detected_count}/{len(expected_topics)} features)")

        if missed:
            print(f"   Missed: {', '.join(missed)}")
            results["missed_features"].append({
                "file_id": file_id,
                "missed": list(missed)
            })

        if false_pos:
            print(f"   False positives: {', '.join(false_pos)}")
            results["false_positives"].append({
                "file_id": file_id,
                "false_positives": list(false_pos)
            })

    overall_recall = results["detected_features"] / results["total_features"] * 100 if results["total_features"] > 0 else 0
    avg_recall = sum(results["recall_scores"]) / len(results["recall_scores"]) if results["recall_scores"] else 0

    print(f"\n{'='*60}")
    print(f"Overall Topic Detection Recall: {overall_recall:.1f}%")
    print(f"Average Recall per Transcript: {avg_recall:.1f}%")
    print(f"Success Criteria: >85% (Fallback: >75%)")

    if overall_recall >= 85:
        print("✅ PASS - Exceeds target")
    elif overall_recall >= 75:
        print("⚠️  PASS - Meets fallback threshold")
    else:
        print("❌ FAIL - Below threshold")

    return results


def test_extraction_accuracy(test_results: List[Dict], ground_truth: Dict) -> Dict:
    """Test if extracted responses match ground truth"""

    print(f"\n{'='*60}")
    print("TEST 2: RESPONSE EXTRACTION ACCURACY")
    print(f"{'='*60}\n")

    accuracy_scores = []
    field_accuracies = {
        "currentStatus": [],
        "hasNeed": [],
        "needReasons": [],
        "barriers": [],
        "implementationWillingness": []
    }

    for test_result in test_results:
        file_id = test_result["file_id"]

        if file_id not in ground_truth or not test_result["success"]:
            continue

        gt = ground_truth[file_id]
        agent_response = test_result["result"]

        for gt_feature in gt["features_discussed"]:
            topic = gt_feature["feature"]
            agent_questionnaire = next(
                (q for q in agent_response.get("discoveryQuestionnaires", []) if q["topic"] == topic),
                None
            )

            if not agent_questionnaire:
                accuracy_scores.append(0)
                print(f"❌ {file_id} - {topic}: Not detected")
                continue

            # Calculate field-level accuracy
            correct_fields = 0
            total_fields = 0

            # Check currentStatus
            if "current_status" in gt_feature:
                total_fields += 1
                if agent_questionnaire.get("currentStatus") == gt_feature["current_status"]:
                    correct_fields += 1
                    field_accuracies["currentStatus"].append(1)
                else:
                    field_accuracies["currentStatus"].append(0)

            # Check hasNeed
            if "has_need" in gt_feature:
                total_fields += 1
                if agent_questionnaire.get("hasNeed") == gt_feature["has_need"]:
                    correct_fields += 1
                    field_accuracies["hasNeed"].append(1)
                else:
                    field_accuracies["hasNeed"].append(0)

            # Check needReasons (partial credit for overlap)
            if gt_feature.get("need_reasons"):
                total_fields += 1
                agent_reasons = [r.get("reason", "") for r in agent_questionnaire.get("needReasons", [])]

                # Fuzzy matching: check if any keyword overlaps
                matches = 0
                for gt_reason in gt_feature["need_reasons"]:
                    for agent_reason in agent_reasons:
                        if any(keyword in agent_reason for keyword in gt_reason.split()):
                            matches += 1
                            break

                reason_score = matches / len(gt_feature["need_reasons"]) if gt_feature["need_reasons"] else 0
                correct_fields += reason_score
                field_accuracies["needReasons"].append(reason_score)

            # Check barriers
            if gt_feature.get("barriers"):
                total_fields += 1
                agent_barriers = [b.get("type", "") for b in agent_questionnaire.get("barriers", [])]
                gt_barriers = gt_feature["barriers"]

                matches = len(set(agent_barriers) & set(gt_barriers))
                barrier_score = matches / len(gt_barriers) if gt_barriers else 0
                correct_fields += barrier_score
                field_accuracies["barriers"].append(barrier_score)

            # Check implementationWillingness
            if "implementation_willingness" in gt_feature:
                total_fields += 1
                if agent_questionnaire.get("implementationWillingness") == gt_feature["implementation_willingness"]:
                    correct_fields += 1
                    field_accuracies["implementationWillingness"].append(1)
                else:
                    field_accuracies["implementationWillingness"].append(0)

            field_accuracy = correct_fields / total_fields * 100 if total_fields > 0 else 0
            accuracy_scores.append(field_accuracy)

            status = "✅" if field_accuracy >= 80 else "⚠️" if field_accuracy >= 60 else "❌"
            print(f"{status} {file_id} - {topic}: {field_accuracy:.1f}% accuracy")

    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0

    print(f"\n{'='*60}")
    print(f"Average Extraction Accuracy: {avg_accuracy:.1f}%")
    print(f"Success Criteria: >75% (Fallback: >65%)")

    # Field-level breakdown
    print(f"\nField-Level Accuracy:")
    for field, scores in field_accuracies.items():
        if scores:
            avg = sum(scores) / len(scores) * 100
            print(f"  {field}: {avg:.1f}%")

    if avg_accuracy >= 75:
        print("\n✅ PASS - Exceeds target")
    elif avg_accuracy >= 65:
        print("\n⚠️  PASS - Meets fallback threshold")
    else:
        print("\n❌ FAIL - Below threshold")

    return {
        "average_accuracy": avg_accuracy,
        "accuracy_scores": accuracy_scores,
        "field_accuracies": field_accuracies
    }


def main():
    parser = argparse.ArgumentParser(description="POC 6: Test Questionnaire Extraction Accuracy")
    parser.add_argument("--test-dir", type=str, required=True, help="Directory containing test transcripts")
    parser.add_argument("--api-key", type=str, help="Gemini API key (or set GEMINI_API_KEY env var)")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: Please provide --api-key or set GEMINI_API_KEY environment variable")
        return

    # Load test transcripts
    test_dir = Path(args.test_dir)
    transcript_files = list(test_dir.glob("test_*.json"))

    if not transcript_files:
        print(f"Error: No test transcript files found in {test_dir}")
        return

    print(f"Found {len(transcript_files)} test transcripts")

    # Initialize extractor
    extractor = QuestionnaireExtractor(api_key)

    # Extract questionnaires
    print(f"\n{'='*60}")
    print("EXTRACTING QUESTIONNAIRES")
    print(f"{'='*60}\n")

    test_results = []
    total_duration = 0

    for file_path in transcript_files:
        file_id, transcript = load_transcript(file_path)

        print(f"Processing {file_id}... ", end="", flush=True)
        result = extractor.extract_questionnaire(transcript)

        test_results.append({
            "file_id": file_id,
            **result
        })

        total_duration += result["duration"]

        if result["success"]:
            num_features = len(result["result"].get("discoveryQuestionnaires", []))
            print(f"✅ {result['duration']:.2f}s, {num_features} features")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")

    print(f"\nTotal extraction time: {total_duration:.2f}s")
    print(f"Average time per transcript: {total_duration/len(test_results):.2f}s")

    # Run tests
    topic_results = test_topic_detection(test_results, GROUND_TRUTH)
    extraction_results = test_extraction_accuracy(test_results, GROUND_TRUTH)

    # Overall assessment
    print(f"\n{'='*60}")
    print("POC 6 OVERALL ASSESSMENT")
    print(f"{'='*60}\n")

    topic_recall = topic_results["detected_features"] / topic_results["total_features"] * 100 if topic_results["total_features"] > 0 else 0
    extraction_accuracy = extraction_results["average_accuracy"]

    overall_pass = topic_recall >= 75 and extraction_accuracy >= 65

    print(f"Topic Detection Recall: {topic_recall:.1f}% (Target: >85%, Fallback: >75%)")
    print(f"Extraction Accuracy: {extraction_accuracy:.1f}% (Target: >75%, Fallback: >65%)")
    print(f"\nOverall Result: {'✅ PASS' if overall_pass else '❌ FAIL'}")

    # Save results
    results_summary = {
        "test_count": len(test_results),
        "total_duration": total_duration,
        "topic_detection": {
            "recall": topic_recall,
            "total_features": topic_results["total_features"],
            "detected_features": topic_results["detected_features"],
            "missed": topic_results["missed_features"],
            "false_positives": topic_results["false_positives"]
        },
        "extraction_accuracy": {
            "average": extraction_accuracy,
            "scores": extraction_results["accuracy_scores"],
            "field_accuracies": {
                field: sum(scores) / len(scores) * 100 if scores else 0
                for field, scores in extraction_results["field_accuracies"].items()
            }
        },
        "overall_pass": overall_pass
    }

    output_file = Path(__file__).parent / "poc6_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
