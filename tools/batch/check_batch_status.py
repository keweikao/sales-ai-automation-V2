"""
Dynamic Batch 狀態檢查工具

檢查已提交的批次轉錄請求狀態。

用法：
    python tools/batch/check_batch_status.py
"""

import os
import sys
import json
import logging

from google.cloud import speech_v2
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
BATCH_STATE_FILE = os.path.join(os.path.dirname(__file__), ".batch_state.json")


def load_state() -> dict:
    """載入批次狀態"""
    if not os.path.exists(BATCH_STATE_FILE):
        logger.error(f"找不到狀態檔案: {BATCH_STATE_FILE}")
        logger.info("請先執行 submit_dynamic_batch.py 提交批次請求")
        sys.exit(1)
        
    with open(BATCH_STATE_FILE, "r") as f:
        return json.load(f)


def check_status():
    """檢查批次處理狀態"""
    state = load_state()
    
    # Support both single operation (legacy) and list of operations
    operations_data = state.get("operations", [])
    if not operations_data and state.get("operation_name"):
        operations_data = [{
            "name": state.get("operation_name"),
            "output_uri": state.get("output_uri")
        }]
    
    if not operations_data:
        logger.error("狀態檔案中找不到 operations")
        sys.exit(1)
    
    logger.info("檢查批次狀態...")
    logger.info(f"  提交時間: {state.get('submitted_at')}")
    logger.info(f"  案件數量: {state.get('case_count')}")
    logger.info(f"  批次數量: {len(operations_data)}")
    
    # Initialize Speech client
    speech_client = speech_v2.SpeechClient(
        client_options=ClientOptions(
            api_endpoint=f"{LOCATION}-speech.googleapis.com"
        )
    )
    
    all_done = True
    completed_count = 0
    
    print("\n" + "=" * 60)
    print("📊 批次處理狀態")
    print("-" * 60)
    
    for i, op_data in enumerate(operations_data, 1):
        op_name = op_data["name"]
        output_uri = op_data["output_uri"]
        
        try:
            # Use the operations client
            # The operations_client.get_operation method expects the name as a string, not a request object
            operation = speech_client._transport.operations_client.get_operation(op_name)
            
            print(f"\n批次 {i}/{len(operations_data)}: {op_name.split('/')[-1]}")
            
            if operation.done:
                completed_count += 1
                if operation.error.code:
                    print("  ❌ 狀態: 失敗")
                    print(f"     錯誤: {operation.error.message}")
                else:
                    print("  ✅ 狀態: 完成")
                    print(f"     輸出: {output_uri}")
            else:
                all_done = False
                print("  ⏳ 狀態: 處理中...")
                
                # Check metadata for progress if available
                if operation.metadata:
                    try:
                        from google.cloud.speech_v2.types import cloud_speech
                        metadata = cloud_speech.BatchRecognizeMetadata()
                        operation.metadata.Unpack(metadata)
                        
                        progress_percent = getattr(metadata, 'progress_percent', None)
                        if progress_percent is not None:
                            print(f"     進度: {progress_percent}%")
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"  檢查狀態失敗: {e}")
            all_done = False

    print("-" * 60)
    if all_done:
        print("\n✅ 所有批次處理完成！")
        print("\n📋 後續步驟:")
        print("   執行以下命令處理結果:")
        print("   python tools/batch/process_batch_results.py")
    else:
        print(f"\n⏳ 進度: {completed_count}/{len(operations_data)} 批次完成")
        print("\n⏰ Dynamic Batch 通常需要 1-24 小時完成")
        print("   請稍後再執行此命令檢查狀態")
    
    print("=" * 60)
    
    return all_done


def main():
    check_status()


if __name__ == "__main__":
    main()
