"""
Dynamic Batch 結果處理工具 (修正版)

下載批次轉錄結果，解析並更新 Firestore。
支援 Speech V2 Dynamic Batch 輸出格式。
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Optional
import re

from google.cloud import firestore, storage, tasks_v2

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
            logger.warning("Cloud Tasks client 初始化失敗，內容更新後將無法自動觸發分析")
    
    def load_state(self) -> dict:
        """載入批次狀態"""
        if not os.path.exists(BATCH_STATE_FILE):
            logger.error(f"找不到狀態檔案: {BATCH_STATE_FILE}")
            sys.exit(1)
            
        with open(BATCH_STATE_FILE, "r") as f:
            return json.load(f)
    
    def download_results(self, output_uri: str, case_mapping: Dict[str, str]) -> Dict[str, str]:
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
        
        results = {}
        
        for blob in blobs:
            if not blob.name.endswith(".json"):
                continue
                
            logger.info(f"  處理: {blob.name}")
            
            try:
                # 1. 尋找匹配的原始音檔 URI
                # 輸出檔名格式通常為: [bucket]/[prefix]/[audio_filename]_transcript_[op_id].json
                # 我們嘗試尋找 mapping 中包含此檔名的 URI
                filename_without_json = os.path.basename(blob.name).replace(".json", "")
                # 移除 _transcript_... 部分
                match = re.search(r"(.+)_transcript_[a-f0-9-]+", filename_without_json)
                if match:
                    base_audio_name = match.group(1)
                else:
                    base_audio_name = filename_without_json
                
                audio_uri = None
                for uri in case_mapping.keys():
                    if base_audio_name in uri:
                        audio_uri = uri
                        break
                
                if not audio_uri:
                    logger.warning(f"    無法為 {blob.name} 找到對應的原始音檔 URI")
                    continue
                
                # 2. 下載並解析 JSON
                content = blob.download_as_text()
                data = json.loads(content)
                
                # Speech V2 output Format: {"results": [...]}
                transcription = self._parse_v2_results(data.get("results", []))
                if transcription:
                    results[audio_uri] = transcription
                    logger.info(f"    成功解析: {audio_uri} ({len(transcription['segments'])} segments)")
                        
            except Exception as e:
                logger.error(f"  處理 {blob.name} 失敗: {e}")
        
        return results
    
    def _parse_v2_results(self, results_api: List[dict]) -> Optional[Dict]:
        """解析 Speech V2 的結果列表"""
        if not results_api:
            return None
        
        segments = []
        full_text_parts = []
        speakers = set()
        
        for res in results_api:
            alternatives = res.get("alternatives", [])
            if not alternatives:
                continue
            
            alt = alternatives[0]
            text = alt.get("transcript", "")
            if not text:
                continue
                
            full_text_parts.append(text)
            
            # 處理詞級別資訊和說話者
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
                        current_segment["text"] += word # 中文不加空格
                        current_segment["end"] = end_time
                
                if current_segment:
                    segments.append(current_segment)
            else:
                # 如果沒有 words 資訊，將整個 alternative 作為一個 segment
                segments.append({
                    "start": 0.0,
                    "end": 0.0,
                    "speaker": "Speaker",
                    "text": text,
                })
        
        full_text = "".join(full_text_parts) # 中文合併
        
        return {
            "text": full_text,
            "full_text": full_text,
            "segments": segments,
            "speakers": list(speakers) if speakers else ["Speaker"],
            "engine": "dynamic_batch",
            "model": "chirp_2",
        }
    
    def _parse_duration(self, duration_str: str) -> float:
        """解析 duration 字串 (e.g., '1.500s')"""
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
            
            logger.info(f"  ✅ 已更新 {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ 更新 {case_id} 失敗: {e}")
            return False
    
    def trigger_analysis(self, case_id: str) -> bool:
        """觸發分析服務"""
        if not self.tasks_client:
            return False
        
        try:
            parent = self.tasks_client.queue_path(
                PROJECT_ID, TASKS_LOCATION, TASKS_QUEUE
            )
            
            # 使用 OIDC Token 認證
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{ANALYSIS_SERVICE_URL}/analyze",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"caseId": case_id}).encode(),
                    "oidc_token": {
                        "service_account_email": f"{PROJECT_ID}@appspot.gserviceaccount.com" # 假設預設 SA
                    }
                }
            }
            
            # 嘗試取得目前的分析服務 URL
            try:
                self.tasks_client.create_task(parent=parent, task=task)
                logger.info(f"    已觸發 {case_id} 的分析")
                return True
            except Exception as te:
                logger.warning(f"    觸發分析失敗 (可能是 SA 權限問題): {te}")
                return False
            
        except Exception as e:
            logger.error(f"觸發 {case_id} 分析失敗: {e}")
            return False
    
    def process(self, trigger_analysis: bool = False):
        """處理批次結果"""
        state = self.load_state()
        operations_data = state.get("operations", [])
        case_mapping = state.get("case_mapping", {})
        
        if not operations_data:
            logger.error("找不到操作狀態")
            return
        
        print("\n" + "=" * 60)
        print("📊 處理結果")
        print("-" * 60)
        
        total_success = 0
        total_fail = 0
        
        for i, op_data in enumerate(operations_data, 1):
            output_uri = op_data["output_uri"]
            print(f"\n批次 {i}/{len(operations_data)}: 下載與解析...")
            
            try:
                results = self.download_results(output_uri, case_mapping)
            except Exception as e:
                logger.error(f"下載失敗 {output_uri}: {e}")
                continue
            
            if not results:
                logger.warning("  沒有找到任何有效結果")
                continue
            
            # 更新 Firestore
            batch_success = 0
            batch_fail = 0
            
            for audio_uri, transcription in results.items():
                case_id = case_mapping.get(audio_uri)
                
                if not case_id:
                    logger.warning(f"  找不到 {audio_uri} 對應的 case_id")
                    continue
                
                # 更新 Firestore
                if self.update_firestore(case_id, transcription):
                    batch_success += 1
                    total_success += 1
                    
                    # 觸發分析
                    if trigger_analysis:
                        self.trigger_analysis(case_id)
                else:
                    batch_fail += 1
                    total_fail += 1
            
            print(f"  批次摘要: ✅ 成功: {batch_success}, ❌ 失敗: {batch_fail}")
        
        print("-" * 60)
        print(f"總計成功更新: {total_success} 案")
        print(f"總計失敗: {total_fail}")
        print("=" * 60)
        
        # 標記完成
        if total_success > 0:
            completed_file = BATCH_STATE_FILE.replace(".json", ".completed.json")
            if os.path.exists(BATCH_STATE_FILE):
                os.rename(BATCH_STATE_FILE, completed_file)
                logger.info(f"已完成。狀態檔案移至: {completed_file}")


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
