"""
Summary Sender - 處理「發送給客戶」按鈕互動

功能:
1. 處理 Slack 按鈕點擊
2. 驗證客戶電話
3. 調用 SMS 服務
4. 更新 Firestore 狀態
5. 回覆 Slack 確認訊息

Migration note: From src/slack_app/interactions/summary_sender.py
"""

import logging
import os
from typing import Dict, Any

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

logger = logging.getLogger(__name__)


class SummarySender:
    """處理會議記錄發送給客戶的互動"""

    def __init__(self, slack_client: WebClient, db_client: firestore.Client):
        """
        初始化 Summary Sender

        Args:
            slack_client: Slack SDK WebClient
            db_client: Firestore client
        """
        self.client = slack_client
        self.db = db_client
        self.sms_service_url = os.getenv('SMS_SERVICE_URL')
        self.sms_internal_token = os.getenv('SMS_INTERNAL_TOKEN')

    def handle_send_to_customer(
        self,
        case_id: str,
        user_id: str,
        channel_id: str,
        message_ts: str
    ) -> Dict[str, Any]:
        """
        處理「發送給客戶」按鈕點擊

        Args:
            case_id: 案件 ID
            user_id: 點擊按鈕的使用者 ID
            channel_id: Slack 頻道 ID
            message_ts: 訊息時間戳記

        Returns:
            Slack 回應字典
        """
        try:
            # 1. 從 Firestore 獲取案件資訊
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                logger.error(f"Case {case_id} not found")
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ 找不到案件 {case_id}"
                }

            case_data = case_doc.to_dict()

            # 2. 驗證客戶電話
            customer_phone = case_data.get('customerPhone')
            customer_name = case_data.get('customerName', '客戶')

            if not customer_phone:
                logger.warning(f"Case {case_id} has no customer phone")
                return {
                    "response_type": "ephemeral",
                    "text": "❌ 此案件缺少客戶電話，無法發送簡訊"
                }

            # 3. 檢查是否已發送
            delivery = case_data.get('delivery', {})
            if delivery.get('smsStatus') == 'sent':
                sent_at = delivery.get('smsSentAt')
                return {
                    "response_type": "ephemeral",
                    "text": f"⚠️ 此案件已於 {sent_at} 發送簡訊給客戶"
                }

            # 4. 檢查 SMS 服務配置
            if not self.sms_service_url:
                logger.error("SMS_SERVICE_URL not configured")
                return {
                    "response_type": "ephemeral",
                    "text": "❌ SMS 服務尚未配置，請聯絡技術支援"
                }

            # 5. 調用 SMS 服務
            logger.info(f"Sending SMS for case {case_id} to {customer_phone}")

            headers = {
                'Content-Type': 'application/json'
            }
            if self.sms_internal_token:
                headers['Authorization'] = f'Bearer {self.sms_internal_token}'

            payload = {
                'caseId': case_id,
                'customerPhone': customer_phone,
                'customerName': customer_name
            }

            response = requests.post(
                f"{self.sms_service_url}/send-sms",
                json=payload,
                headers=headers,
                timeout=30
            )

            # 6. 處理回應
            if response.status_code == 200:
                result = response.json()
                summary_url = result.get('summaryUrl', '')

                logger.info(f"SMS sent successfully for case {case_id}")

                # 更新 Firestore（SMS 服務已更新，這裡只記錄發送者）
                case_ref.update({
                    'delivery.smsSentBy': user_id,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })

                # 發送確認訊息到 thread
                try:
                    self.client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=message_ts,
                        text=f"✅ 會議記錄已發送給 {customer_name} ({customer_phone})\n\n"
                             f"📱 簡訊內容包含網頁連結：\n{summary_url}"
                    )
                except SlackApiError as e:
                    logger.error(f"Failed to send confirmation message: {e}")

                return {
                    "response_type": "ephemeral",
                    "text": f"✅ 會議記錄已成功發送給 {customer_name}"
                }
            else:
                # 發送失敗
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')

                logger.error(f"SMS sending failed for case {case_id}: {error_msg}")

                return {
                    "response_type": "ephemeral",
                    "text": f"❌ 發送失敗: {error_msg}\n請稍後再試或聯絡技術支援"
                }

        except requests.RequestException as e:
            logger.error(f"HTTP request to SMS service failed: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"❌ 無法連線到 SMS 服務: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error handling send to customer: {e}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"❌ 系統錯誤: {str(e)}"
            }
