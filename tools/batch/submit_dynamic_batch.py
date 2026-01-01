"""
Dynamic Batch 批次提交工具

使用 Google Speech-to-Text V2 Dynamic Batch 模式處理待轉錄音檔。
成本：$0.003/分鐘（比標準 $0.016 便宜 81%）

用法：
    python tools/batch/submit_dynamic_batch.py [--dry-run]
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import json

from google.cloud import firestore, storage
from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
LOCATION = os.environ.get("GCP_LOCATION", "asia-southeast1")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "sales-ai-audio-bucket")
BATCH_STATE_FILE = os.path.join(os.path.dirname(__file__), ".batch_state.json")


class DynamicBatchSubmitter:
    """提交 Dynamic Batch 轉錄請求"""
    
    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location
        
        # Initialize clients
        self.db = firestore.Client(project=project_id)
        self.storage_client = storage.Client()
        
        # Speech V2 Client with regional endpoint
        self.speech_client = speech_v2.SpeechClient(
            client_options=ClientOptions(
                api_endpoint=f"{location}-speech.googleapis.com"
            )
        )
        
        # Recognizer configuration
        self.recognizer_id = "dynamic-batch-recognizer-chirp3"
        self.recognizer_path = f"projects/{project_id}/locations/{location}/recognizers/{self.recognizer_id}"
        
    def get_pending_cases(self) -> List[Dict]:
        """
        查詢 Firestore 取得待轉錄案件
        條件：case ID 以 202512 開頭，且無轉錄結果
        """
        logger.info("查詢待轉錄案件...")
        
        cases_ref = self.db.collection("cases")
        all_docs = list(cases_ref.stream())
        
        # Filter for 202512 cases
        pending_cases = []
        
        for doc in all_docs:
            case_id = doc.id
            
            # Only process 202512* cases
            if not case_id.startswith("202512"):
                continue
                
            data = doc.to_dict()
            status = data.get("status", "unknown")
            transcription = data.get("transcription")
            gcs_uri = data.get("gcsUri")
            
            # Skip if already has transcription
            has_transcription = (
                transcription is not None and 
                isinstance(transcription, dict) and 
                (transcription.get("text") or transcription.get("segments"))
            )
            
            if has_transcription:
                continue
                
            # Skip if no GCS URI
            if not gcs_uri:
                logger.warning(f"案件 {case_id} 無 GCS URI，跳過")
                continue
                
            pending_cases.append({
                "case_id": case_id,
                "gcs_uri": gcs_uri,
                "customer_name": data.get("customerName", "N/A"),
                "rep_name": data.get("repName", "N/A"),
                "status": status,
            })
        
        logger.info(f"找到 {len(pending_cases)} 個待轉錄案件")
        return pending_cases
    
    def ensure_recognizer(self):
        """確保 Recognizer 存在，不存在則建立"""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        
        try:
            self.speech_client.get_recognizer(name=self.recognizer_path)
            logger.info(f"Recognizer {self.recognizer_id} 已存在")
        except Exception:
            logger.info(f"建立 Recognizer {self.recognizer_id}...")
            
            features = cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True,
                enable_automatic_punctuation=True,
            )
            
            request = cloud_speech.CreateRecognizerRequest(
                parent=parent,
                recognizer_id=self.recognizer_id,
                recognizer=cloud_speech.Recognizer(
                    default_recognition_config=cloud_speech.RecognitionConfig(
                        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                        language_codes=["cmn-Hant-TW"],
                        model="chirp_2",  # Chirp 2 for Dynamic Batch
                        features=features,
                    )
                ),
            )
            
            operation = self.speech_client.create_recognizer(request=request)
            operation.result(timeout=120)
            logger.info(f"Recognizer {self.recognizer_id} 建立完成")
    
    def submit_batch(self, cases: List[Dict], dry_run: bool = False) -> List[str]:
        """
        提交 Dynamic Batch 請求
        
        Args:
            cases: 待處理案件列表
            dry_run: 若為 True，只印出會處理的案件，不實際提交
            
        Returns:
            List of Operation names
        """
        if not cases:
            logger.info("無待處理案件")
            return []
            
        # Prepare file list
        files = []
        case_mapping = {}  # gcs_uri -> case_id
        
        for case in cases:
            gcs_uri = case["gcs_uri"]
            case_id = case["case_id"]
            
            files.append(cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri))
            case_mapping[gcs_uri] = case_id
            
            logger.info(f"  - {case_id}: {case['customer_name']} ({gcs_uri})")
        
        if dry_run:
            logger.info(f"\n[DRY RUN] 會提交 {len(files)} 個檔案到 Dynamic Batch")
            return []
        
        # Ensure recognizer exists
        self.ensure_recognizer()
        
        # Split into batches of 15 (API limit)
        batch_size = 15
        operations = []
        
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i + batch_size]
            logger.info(f"\n提交批次 {i//batch_size + 1} (檔案 {i+1} - {i+len(batch_files)})...")
            
            # Output configuration
            output_uri = f"gs://{OUTPUT_BUCKET}/batch_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}_batch{i//batch_size + 1}/"
            
            output_config = cloud_speech.RecognitionOutputConfig(
                gcs_output_config=cloud_speech.GcsOutputConfig(uri=output_uri)
            )
            
            # Processing strategy - Dynamic Batch
            processing_strategy = cloud_speech.BatchRecognizeRequest.ProcessingStrategy.DYNAMIC_BATCHING
            
            request = cloud_speech.BatchRecognizeRequest(
                recognizer=self.recognizer_path,
                files=batch_files,
                recognition_output_config=output_config,
                processing_strategy=processing_strategy,
            )
            
            operation = self.speech_client.batch_recognize(request=request)
            op_name = operation.operation.name
            operations.append({
                "name": op_name,
                "output_uri": output_uri
            })
            
            logger.info(f"  Operation: {op_name}")
            logger.info(f"  輸出目錄: {output_uri}")
        
        logger.info(f"\n✅ 所有批次已提交！共 {len(operations)} 個作業")
        
        # Save state
        state = {
            "operations": operations,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "case_count": len(cases),
            "case_mapping": case_mapping,
            "cases": cases,
        }
        
        with open(BATCH_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  狀態已儲存: {BATCH_STATE_FILE}")
        
        return [op["name"] for op in operations]


def main():
    parser = argparse.ArgumentParser(description="提交 Dynamic Batch 轉錄請求")
    parser.add_argument("--dry-run", action="store_true", help="只顯示會處理的案件，不實際提交")
    args = parser.parse_args()
    
    submitter = DynamicBatchSubmitter(PROJECT_ID, LOCATION)
    
    # Get pending cases
    cases = submitter.get_pending_cases()
    
    if not cases:
        logger.info("🎉 沒有待轉錄的案件！")
        return
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 待轉錄案件摘要")
    print("-" * 60)
    print(f"案件數量: {len(cases)}")
    print(f"預估成本: ${len(cases) * 30 * 0.003:.2f} (假設每個 30 分鐘)")
    print("=" * 60 + "\n")
    
    # Submit batch
    operation_name = submitter.submit_batch(cases, dry_run=args.dry_run)
    
    if operation_name:
        print("\n" + "=" * 60)
        print("📋 後續步驟")
        print("-" * 60)
        print("1. 執行以下命令檢查狀態:")
        print(f"   python tools/batch/check_batch_status.py")
        print("\n2. 處理完成後，執行以下命令處理結果:")
        print(f"   python tools/batch/process_batch_results.py")
        print("=" * 60)


if __name__ == "__main__":
    main()
