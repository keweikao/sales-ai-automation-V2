"""
Dynamic Batch 結果處理工具

下載批次轉錄結果，解析並更新 Firestore。

用法：
    python tools/batch/process_batch_results.py [--trigger-analysis]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import re

from google.cloud import firestore, storage, tasks_v2
from google.cloud.speech_v2.types import cloud_speech

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
LOCATION = os.environ.get("GCP_LOCATION", "asia-southeast1")
BATCH_STATE_FILE = os.path.join(os.path.dirname(__file__), ".batch_state.json")

# Analysis Service configuration
ANALYSIS_SERVICE_URL = os.environ.get(
    "ANALYSIS_SERVICE_URL",
    "https://analysis-service-497329205771.asia-east1.run.app"
)
TASKS_QUEUE = "analysis-queue"
TASKS_LOCATION = "asia-east1"


class BatchResultProcessor:
    """處理 Dynamic Batch 結果"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.db = firestore.Client(project=project_id)
        self.storage_client = storage.Client()
        
        try:
            self.tasks_client = tasks_v2.CloudTasksClient()
        except Exception:
            self.tasks_client = None
            logger.warning("Cloud Tasks client 初始化失敗，將無法觸發分析")
    
    def load_state(self) -> dict:
        """載入批次狀態"""
        if not os.path.exists(BATCH_STATE_FILE):
            logger.error(f"找不到狀態檔案: {BATCH_STATE_FILE}")
            sys.exit(1)
            
        with open(BATCH_STATE_FILE, "r") as f:
            return json.load(f)
    
    def download_results(self, output_uri: str) -> Dict[str, str]:
        """
        從 GCS 下載結果檔案
        
        Returns:
            Dict mapping original GCS URI to transcription result
        """
        logger.info(f"從 {output_uri} 下載結果...")
        
        # Parse GCS URI
        if not output_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {output_uri}")
        
        parts = output_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        
        bucket = self.storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        logger.info(f"找到 {len(blobs)} 個結果檔案")
        
        results = {}
        
        for blob in blobs:
            if not blob.name.endswith(".json"):
                continue
                
            logger.info(f"  處理: {blob.name}")
            
            try:
                content = blob.download_as_text()
                data = json.loads(content)
                
                # Parse the result
                for uri, result in data.get("results", {}).items():
                    transcription = self._parse_result(result)
                    if transcription:
                        results[uri] = transcription
                        
            except Exception as e:
                logger.error(f"處理 {blob.name} 失敗: {e}")
        
        return results
    
    def _parse_result(self, result: dict) -> Optional[Dict]:
        """解析單一轉錄結果"""
        if result.get("error"):
            logger.warning(f"轉錄錯誤: {result['error']}")
            return None
        
        transcript = result.get("transcript", {})
        results = transcript.get("results", [])
        
        segments = []
        full_text_parts = []
        speakers = set()
        
        for res in results:
            alternatives = res.get("alternatives", [])
            if not alternatives:
                continue
            
            alt = alternatives[0]
            text = alt.get("transcript", "")
            full_text_parts.append(text)
            
            # Process words
            words = alt.get("words", [])
            if words:
                current_segment = None
                
                for word_info in words:
                    word = word_info.get("word", "")
                    start_time = self._parse_duration(word_info.get("startOffset", "0s"))
                    end_time = self._parse_duration(word_info.get("endOffset", "0s"))
                    speaker = word_info.get("speakerLabel", "Speaker")
                    
                    if speaker:
                        speakers.add(speaker)
                    
                    if current_segment is None or current_segment["speaker"] != speaker:
                        if current_segment:
                            segments.append(current_segment)
                        current_segment = {
                            "start": start_time,
                            "end": end_time,
                            "speaker": speaker or "Speaker",
                            "text": word,
                        }
                    else:
                        current_segment["text"] += " " + word
                        current_segment["end"] = end_time
                
                if current_segment:
                    segments.append(current_segment)
        
        full_text = " ".join(full_text_parts)
        
        # Fallback segment if no word-level info
        if not segments and full_text:
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "speaker": "Speaker",
                "text": full_text,
            })
        
        return {
            "text": full_text,
            "full_text": full_text,
            "segments": segments,
            "speakers": list(speakers),
            "engine": "dynamic_batch",
            "model": "chirp_2",
        }
    
    def _parse_duration(self, duration_str: str) -> float:
        """解析 duration 字串 (e.g., '1.5s', '0.123s')"""
        if not duration_str:
            return 0.0
        
        match = re.match(r"([\d.]+)s", duration_str)
        if match:
            return float(match.group(1))
        return 0.0
    
    def update_firestore(self, case_id: str, transcription: Dict) -> bool:
        """更新 Firestore 中的轉錄結果"""
        try:
            case_ref = self.db.collection("cases").document(case_id)
            
            case_ref.update({
                "transcription": transcription,
                "status": "transcribed",
                "transcribedAt": firestore.SERVER_TIMESTAMP,
                "transcriptionEngine": "dynamic_batch",
            })
            
            logger.info(f"✅ 已更新 {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新 {case_id} 失敗: {e}")
            return False
    
    def trigger_analysis(self, case_id: str) -> bool:
        """觸發分析服務"""
        if not self.tasks_client:
            logger.warning(f"無法觸發 {case_id} 的分析（Cloud Tasks 未初始化）")
            return False
        
        try:
            parent = self.tasks_client.queue_path(
                PROJECT_ID, TASKS_LOCATION, TASKS_QUEUE
            )
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{ANALYSIS_SERVICE_URL}/analyze",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"caseId": case_id}).encode(),
                }
            }
            
            self.tasks_client.create_task(parent=parent, task=task)
            logger.info(f"  已觸發 {case_id} 的分析")
            return True
            
        except Exception as e:
            logger.error(f"觸發 {case_id} 分析失敗: {e}")
            return False
    
    def process(self, trigger_analysis: bool = False):
        """處理批次結果"""
        state = self.load_state()
        
        # Support both single operation (legacy) and list of operations
        operations_data = state.get("operations", [])
        if not operations_data and state.get("output_uri"):
            operations_data = [{
                "name": state.get("operation_name", "unknown"),
                "output_uri": state.get("output_uri")
            }]
            
        case_mapping = state.get("case_mapping", {})
        
        if not operations_data:
            logger.error("找不到輸出 URI")
            return
        
        print("\n" + "=" * 60)
        print("📊 處理結果")
        print("-" * 60)
        
        total_success = 0
        total_fail = 0
        
        for i, op_data in enumerate(operations_data, 1):
            output_uri = op_data["output_uri"]
            print(f"\n批次 {i}/{len(operations_data)}: 下載結果...")
            
            # Download and parse results
            try:
                results = self.download_results(output_uri)
            except Exception as e:
                logger.error(f"下載失敗 {output_uri}: {e}")
                continue
            
            if not results:
                logger.warning("  沒有找到任何結果")
                continue
            
            # Update Firestore
            batch_success = 0
            batch_fail = 0
            
            for gcs_uri, transcription in results.items():
                case_id = case_mapping.get(gcs_uri)
                
                if not case_id:
                    # Try to extract case_id from URI
                    match = re.search(r"/uploads/([^/]+)/", gcs_uri)
                    if match:
                        case_id = match.group(1)
                
                if not case_id:
                    logger.warning(f"  找不到 {gcs_uri} 對應的 case_id")
                    continue
                
                # Update Firestore
                if self.update_firestore(case_id, transcription):
                    batch_success += 1
                    total_success += 1
                    
                    # Trigger analysis if requested
                    if trigger_analysis:
                        self.trigger_analysis(case_id)
                else:
                    batch_fail += 1
                    total_fail += 1
            
            print(f"  ✅ 成功: {batch_success}, ❌ 失敗: {batch_fail}")
        
        print("-" * 60)
        print(f"總計成功: {total_success}")
        print(f"總計失敗: {total_fail}")
        print("=" * 60)
        
        # Clean up state file
        if total_success > 0 and total_fail == 0:
            # Rename state file to indicate completion
            completed_file = BATCH_STATE_FILE.replace(".json", ".completed.json")
            os.rename(BATCH_STATE_FILE, completed_file)
            logger.info(f"狀態檔案已移至: {completed_file}")


def main():
    parser = argparse.ArgumentParser(description="處理 Dynamic Batch 結果")
    parser.add_argument(
        "--trigger-analysis",
        action="store_true",
        help="處理完成後觸發分析服務"
    )
    args = parser.parse_args()
    
    processor = BatchResultProcessor(PROJECT_ID)
    processor.process(trigger_analysis=args.trigger_analysis)


if __name__ == "__main__":
    main()
