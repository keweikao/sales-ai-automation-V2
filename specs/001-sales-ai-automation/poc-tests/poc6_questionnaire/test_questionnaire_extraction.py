#!/usr/bin/env python3
"""
POC 6: POS Adoption Assessment Accuracy

Tests Agent 5's ability to consolidate feature needs and evaluate POS adoption likelihood.

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


GROUND_TRUTH = {
    "test_01": {
        "features": [
            {"feature": "掃碼點餐", "priority": "high", "status": "未使用"},
            {"feature": "POS點餐系統", "priority": "medium", "status": "使用中"}
        ],
        "adoption": {
            "stage": "high",
            "positive": ["尖峰時段人手不足", "想縮短等候時間"],
            "negative": ["擔心客人不會掃碼"]
        }
    },
    "test_02": {
        "features": [
            {"feature": "POS點餐系統", "priority": "medium", "status": "未使用"},
            {"feature": "成本控管", "priority": "high", "status": "未使用"},
            {"feature": "庫存管理", "priority": "high", "status": "未使用"}
        ],
        "adoption": {
            "stage": "medium",
            "positive": ["想掌握成本", "想提升效率"],
            "negative": ["預算壓力"]
        }
    },
    "test_03": {
        "features": [
            {"feature": "掃碼點餐", "priority": "medium", "status": "考慮中"},
            {"feature": "線上訂位管理", "priority": "medium", "status": "未使用"},
            {"feature": "外送平台整合", "priority": "medium", "status": "考慮中"},
            {"feature": "總部系統", "priority": "high", "status": "未使用"}
        ],
        "adoption": {
            "stage": "high",
            "positive": ["需要整合分店資料", "需要統一報表"],
            "negative": ["舊系統整合難度"]
        }
    },
    "test_05": {
        "features": [
            {"feature": "線上訂位管理", "priority": "high", "status": "未使用"},
            {"feature": "掃碼點餐", "priority": "medium", "status": "未使用"}
        ],
        "adoption": {
            "stage": "high",
            "positive": ["電話訂位太多", "人力不足"],
            "negative": []
        }
    },
    "test_06": {
        "features": [
            {"feature": "掃碼點餐", "priority": "low", "status": "未使用"},
            {"feature": "POS點餐系統", "priority": "low", "status": "使用中"}
        ],
        "adoption": {
            "stage": "low",
            "positive": [],
            "negative": ["老客人不習慣科技", "維持人情味", "不想減少人力"]
        }
    },
    "test_07": {
        "features": [
            {"feature": "外送平台整合", "priority": "high", "status": "未使用"},
            {"feature": "線上點餐接單", "priority": "medium", "status": "未使用"}
        ],
        "adoption": {
            "stage": "high",
            "positive": ["外送平台很多", "想集中管理訂單"],
            "negative": []
        }
    }
}


AGENT5_PROMPT_TEMPLATE = """# Agent 5: POS Adoption Assessment

## 角色
你是 iCHEF 的銷售分析專家，負責閱讀餐飲業務對話，統整客戶所有功能需求並評估「是否會採用 iCHEF POS」的可能性。

## 目標
1. 收整對話中提到的所有功能需求（依 iCHEF 產品目錄分類）。
2. 分析這些需求如何影響 POS 導入意願。
3. 明確指出「成交／不成交」的關鍵因素與引用。

## iCHEF 產品分類（摘自 product-catalog.yaml）
- 點餐與訂單管理：掃碼點餐、多⼈掃碼、套餐加價購、智慧菜單推薦、POS點餐系統、線上點餐接單
- 線上整合服務：線上訂位管理、線上外帶、雲端餐廳、Google整合、LINE整合、外送平台整合、聯絡式外帶服務
- 成本與庫存：會計系統、庫存管理、成本控管
- 業績分析：銷售分析報表、經營數據管理
- 客戶關係：零秒集點、會員管理系統
- 企業級功能：總部系統、連鎖品牌管理
- 其他需求：對話中出現但未列於清單的功能

## 輸出格式（JSON ONLY）
請輸出以下結構：
{
  "posAdoptionSummary": {
    "requiredFeatures": [
      {
        "feature": "掃碼點餐",
        "featureCategory": "點餐與訂單管理",
        "currentStatus": "未使用" | "使用中" | "考慮中" | "曾使用過",
        "priority": "high" | "medium" | "low",
        "evidence": "引用對話原句（<=20字）"
      }
    ],
    "adoptionLikelihood": {
      "stage": "high" | "medium" | "low",
      "score": 0-100,
      "confidence": 0-100,
      "summary": "一句話摘要判斷依據"
    },
    "closingReasons": {
      "positiveDrivers": [
        {
          "reason": "尖峰時段人手不足",
          "quote": "尖峰時段服務生不夠",
          "impact": "high" | "medium" | "low"
        }
      ],
      "negativeFactors": [
        {
          "reason": "擔心客人不會掃碼",
          "quote": "老人家不會用手機掃碼",
          "severity": "high" | "medium" | "low"
        }
      ]
    },
    "recommendedNextSteps": [
      {
        "action": "安排成功案例參訪",
        "owner": "sales" | "customer",
        "urgency": "immediate" | "upcoming" | "low",
        "rationale": "引用或原因（<=25字）"
      }
    ]
  }
}

## 判斷準則
- **priority**：以客戶語氣與痛點嚴重程度判斷（high=關鍵痛點、medium=明確需求、low=潛在/附帶）。
- **stage**：high=積極導入、medium=觀望但願意討論、low=明確排斥。
- **score**：0-100，對應 stage（high>=70、medium=40-69、low<40）。
- **quote**：必須節錄逐字稿原文，保持繁體中文。
- 若無負向因素，可回傳空陣列。

## 請務必
- 僅根據逐字稿內容推論，禁止臆測。
- 所有欄位使用繁體中文，JSON 中不得包含解說文字。
- 若對話無法判斷，將 `stage` 設為 "medium"、`confidence` <= 50，並在 summary 補充原因。

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
        prompt = AGENT5_PROMPT_TEMPLATE.replace("{transcript}", transcript)

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


def normalize(text: str) -> str:
    return text.replace(" ", "").replace("\n", "").lower()


def evaluate_feature_coverage(test_results: List[Dict], ground_truth: Dict) -> Dict:
    print(f"\n{'='*60}")
    print("TEST 1: 功能需求涵蓋率")
    print(f"{'='*60}\n")

    total_expected = 0
    total_detected = 0
    detail: List[Dict] = []

    for test_result in test_results:
        file_id = test_result["file_id"]
        truth = ground_truth.get(file_id)

        if not truth:
            print(f"⚠️  {file_id}: 無對照資料，略過")
            continue

        expected = truth["features"]
        total_expected += len(expected)

        if not test_result["success"]:
            print(f"❌ {file_id}: 提取失敗 ({test_result.get('error')})")
            detail.append({
                "file_id": file_id,
                "matched": 0,
                "expected": len(expected),
                "missed": [f['feature'] for f in expected],
                "extra": []
            })
            continue

        predicted_items = test_result["result"].get("posAdoptionSummary", {}).get("requiredFeatures", [])
        predicted_names = {item.get("feature") for item in predicted_items}

        matched = [f for f in expected if f["feature"] in predicted_names]
        missed = [f["feature"] for f in expected if f["feature"] not in predicted_names]
        extra = [name for name in predicted_names if name not in {f["feature"] for f in expected}]

        total_detected += len(matched)

        status = "✅" if not missed else "⚠️" if matched else "❌"
        print(f"{status} {file_id}: {len(matched)}/{len(expected)} 功能被辨識")
        if missed:
            print(f"   Missed: {', '.join(missed)}")
        if extra:
            print(f"   Extra: {', '.join(extra)}")

        detail.append({
            "file_id": file_id,
            "matched": len(matched),
            "expected": len(expected),
            "missed": missed,
            "extra": extra
        })

    recall = (total_detected / total_expected * 100) if total_expected else 0
    print(f"\n整體功能涵蓋率: {recall:.1f}%")
    print("目標 >85%，Fallback >75%")

    return {
        "recall": recall,
        "detail": detail,
        "total_expected": total_expected,
        "total_detected": total_detected
    }


def match_reasons(predicted: List[Dict], expected: List[str]) -> float:
    if not expected:
        return 1.0 if not predicted else 0.0
    predicted_texts = [normalize(item.get("reason", "") + item.get("quote", "")) for item in predicted]
    hits = 0
    for target in expected:
        target_norm = normalize(target)
        if any(target_norm in text for text in predicted_texts):
            hits += 1
    return hits / len(expected)


def evaluate_adoption_analysis(test_results: List[Dict], ground_truth: Dict) -> Dict:
    print(f"\n{'='*60}")
    print("TEST 2: POS 導入可能性判斷")
    print(f"{'='*60}\n")

    stage_matches = []
    positive_coverages = []
    negative_coverages = []
    summaries = []

    for test_result in test_results:
        file_id = test_result["file_id"]
        truth = ground_truth.get(file_id)
        if not truth or not test_result["success"]:
            continue

        summary = test_result["result"].get("posAdoptionSummary", {})
        adoption = summary.get("adoptionLikelihood", {})
        closing = summary.get("closingReasons", {})
        positives = closing.get("positiveDrivers", [])
        negatives = closing.get("negativeFactors", [])

        stage_correct = adoption.get("stage") == truth["adoption"]["stage"]
        stage_matches.append(1 if stage_correct else 0)

        pos_score = match_reasons(positives, truth["adoption"]["positive"])
        neg_score = match_reasons(negatives, truth["adoption"]["negative"])
        positive_coverages.append(pos_score)
        negative_coverages.append(neg_score)

        status = "✅" if stage_correct and pos_score >= 0.7 and neg_score >= 0.7 else "⚠️" if stage_correct else "❌"
        print(f"{status} {file_id}: stage={'正確' if stage_correct else '錯誤'} pos={pos_score*100:.0f}% neg={neg_score*100:.0f}%")

        summaries.append({
            "file_id": file_id,
            "stage_correct": stage_correct,
            "positive_coverage": pos_score,
            "negative_coverage": neg_score
        })

    stage_accuracy = sum(stage_matches) / len(stage_matches) * 100 if stage_matches else 0
    positive_coverage = sum(positive_coverages) / len(positive_coverages) * 100 if positive_coverages else 0
    negative_coverage = sum(negative_coverages) / len(negative_coverages) * 100 if negative_coverages else 0

    print(f"\nStage 判斷正確率: {stage_accuracy:.1f}%")
    print(f"成交關鍵覆蓋率: {positive_coverage:.1f}%")
    print(f"不成交關鍵覆蓋率: {negative_coverage:.1f}%")
    print("目標：Stage >80%，正／負向覆蓋 >70%")

    return {
        "stage_accuracy": stage_accuracy,
        "positive_coverage": positive_coverage,
        "negative_coverage": negative_coverage,
        "summaries": summaries
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
            num_features = len(result["result"].get("posAdoptionSummary", {}).get("requiredFeatures", []))
            print(f"✅ {result['duration']:.2f}s, {num_features} features")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")

    print(f"\nTotal extraction time: {total_duration:.2f}s")
    print(f"Average time per transcript: {total_duration/len(test_results):.2f}s")

    # Run evaluations
    feature_results = evaluate_feature_coverage(test_results, GROUND_TRUTH)
    adoption_results = evaluate_adoption_analysis(test_results, GROUND_TRUTH)

    # Overall assessment
    print(f"\n{'='*60}")
    print("POC 6 OVERALL ASSESSMENT")
    print(f"{'='*60}\n")

    topic_recall = feature_results["recall"]
    stage_accuracy = adoption_results["stage_accuracy"]
    positive_coverage = adoption_results["positive_coverage"]
    negative_coverage = adoption_results["negative_coverage"]

    overall_pass = (
        topic_recall >= 80 and
        stage_accuracy >= 80 and
        positive_coverage >= 70 and
        negative_coverage >= 70
    )

    print(f"功能涵蓋率: {topic_recall:.1f}% (目標 >85%，Fallback >75%)")
    print(f"Stage 判斷正確率: {stage_accuracy:.1f}% (目標 >80%)")
    print(f"成交關鍵覆蓋率: {positive_coverage:.1f}% (目標 >70%)")
    print(f"不成交關鍵覆蓋率: {negative_coverage:.1f}% (目標 >70%)")
    print(f"\n整體結果: {'✅ PASS' if overall_pass else '❌ FAIL'}")

    # Save results
    results_summary = {
        "test_count": len(test_results),
        "total_duration": total_duration,
        "feature_coverage": feature_results,
        "adoption_analysis": adoption_results,
        "metrics": {
            "feature_recall": topic_recall,
            "stage_accuracy": stage_accuracy,
            "positive_coverage": positive_coverage,
            "negative_coverage": negative_coverage
        },
        "overall_pass": overall_pass
    }

    output_file = Path(__file__).parent / "poc6_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
