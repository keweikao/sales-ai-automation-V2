"""
SMS 服務 - 使用互動資通 EVERY8D API 發送會議記錄簡訊

功能:
1. 接收發送請求 (caseId, customerPhone, customerName)
2. 生成網頁 URL
3. 透過 EVERY8D API 發送 SMS
4. 記錄發送狀態到 Firestore
"""

import logging
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime

import requests
from flask import Flask, request, jsonify
from google.cloud import firestore

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask
app = Flask(__name__)

# 環境變數
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'sales-ai-automation-v2')
EVERY8D_USERNAME = os.getenv('EVERY8D_USERNAME')
EVERY8D_PASSWORD = os.getenv('EVERY8D_PASSWORD')
EVERY8D_API_URL = os.getenv('EVERY8D_API_URL', 'https://api.every8d.com/API21/HTTP/sendSMS.ashx')
SUMMARY_BASE_URL = os.getenv('SUMMARY_BASE_URL', 'https://web-service-497329205771.asia-east1.run.app')
INTERNAL_TOKEN = os.getenv('SMS_INTERNAL_TOKEN')

# 初始化 Firestore
db = firestore.Client(project=GCP_PROJECT_ID)


class EVERY8DSMSService:
    """互動資通 EVERY8D SMS API 整合"""
    
    def __init__(self, username: str, password: str, api_url: str):
        self.username = username
        self.password = password
        self.api_url = api_url
    
    def send_sms(
        self,
        phone: str,
        message: str,
        subject: str = '【iCHEF】'
    ) -> Dict[str, Any]:
        """
        發送簡訊
        
        Args:
            phone: 手機號碼 (09xxxxxxxx)
            message: 簡訊內容
            subject: 簡訊主旨（選填）
        
        Returns:
            發送結果字典
        """
        # 準備 API 參數
        params = {
            'UID': self.username,
            'PWD': self.password,
            'SB': subject,
            'MSG': message,
            'DEST': phone,
            'ST': '',  # 立即發送
        }
        
        try:
            logger.info(f"Sending SMS to {phone}")
            response = requests.get(self.api_url, params=params, timeout=30)
            result = response.text.strip()
            
            logger.info(f"EVERY8D API response: {result}")
            
            # 解析回應
            if result.startswith('-'):
                # 錯誤代碼
                error_codes = {
                    '-1': '帳號密碼錯誤',
                    '-2': '餘額不足',
                    '-3': '簡訊內容不得為空白',
                    '-4': '無效的手機號碼',
                    '-100': '系統發生錯誤'
                }
                error_msg = error_codes.get(result, f'未知錯誤: {result}')
                logger.error(f"EVERY8D API error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': result
                }
            
            # 成功：解析回應
            # 格式: Credit,Sended,Cost,Unsend,BatchID
            parts = result.split(',')
            if len(parts) >= 5:
                return {
                    'success': True,
                    'batch_id': parts[4],
                    'credit_remaining': parts[0],
                    'messages_sent': parts[1],
                    'cost': parts[2],
                    'unsent': parts[3]
                }
            else:
                logger.error(f"Unable to parse EVERY8D response: {result}")
                return {
                    'success': False,
                    'error': f'無法解析 API 回應: {result}'
                }
                
        except requests.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'success': False,
                'error': f'HTTP 請求失敗: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'未預期的錯誤: {str(e)}'
            }


def validate_phone(phone: str) -> Optional[str]:
    """
    驗證並清理手機號碼
    
    Args:
        phone: 原始手機號碼
    
    Returns:
        清理後的手機號碼，如果無效則返回 None
    """
    if not phone:
        return None
    
    # 移除所有非數字字元
    clean = re.sub(r'[^\d]', '', phone)
    
    # 驗證台灣手機格式 (09xxxxxxxx)
    if re.fullmatch(r'09\d{8}', clean):
        return clean
    
    return None


def generate_summary_url(case_id: str) -> str:
    """
    生成會議記錄網頁 URL
    
    Args:
        case_id: 案件 ID
    
    Returns:
        網頁 URL
    """
    return f"{SUMMARY_BASE_URL}/summary/{case_id}"


def compose_sms_message(customer_name: str, summary_url: str) -> str:
    """
    組合簡訊內容
    
    Args:
        customer_name: 客戶姓名
        summary_url: 網頁 URL
    
    Returns:
        簡訊內容
    """
    # 簡訊內容（中文標準簡訊 70 字以內）
    message = f"""【iCHEF】{customer_name} 您好，這是我們今天會議的摘要記錄：
{summary_url}

如有任何問題歡迎隨時聯繫！"""
    
    return message


@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({'status': 'healthy', 'service': 'sms-service'}), 200


@app.route('/send-sms', methods=['POST'])
def send_sms():
    """
    發送會議記錄簡訊
    
    請求格式:
    {
        "caseId": "202512-IC001",
        "customerPhone": "0912345678",
        "customerName": "一畝食鍋老闆"
    }
    """
    # 驗證內部 token
    auth_header = request.headers.get('Authorization')
    if INTERNAL_TOKEN and auth_header != f'Bearer {INTERNAL_TOKEN}':
        logger.warning("Unauthorized SMS request")
        return jsonify({'error': 'Unauthorized'}), 401
    
    # 解析請求
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    case_id = data.get('caseId')
    customer_phone = data.get('customerPhone')
    customer_name = data.get('customerName', '客戶')
    
    # 驗證必填欄位
    if not case_id:
        return jsonify({'error': 'Missing caseId'}), 400
    if not customer_phone:
        return jsonify({'error': 'Missing customerPhone'}), 400
    
    # 驗證手機號碼
    clean_phone = validate_phone(customer_phone)
    if not clean_phone:
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    # 檢查 EVERY8D 憑證
    if not EVERY8D_USERNAME or not EVERY8D_PASSWORD:
        logger.error("EVERY8D credentials not configured")
        return jsonify({'error': 'SMS service not configured'}), 500
    
    try:
        # 生成網頁 URL
        summary_url = generate_summary_url(case_id)
        
        # 組合簡訊內容
        sms_message = compose_sms_message(customer_name, summary_url)
        
        logger.info(f"Sending SMS for case {case_id} to {clean_phone}")
        logger.info(f"Message length: {len(sms_message)} characters")
        
        # 發送簡訊
        sms_service = EVERY8DSMSService(
            username=EVERY8D_USERNAME,
            password=EVERY8D_PASSWORD,
            api_url=EVERY8D_API_URL
        )
        
        result = sms_service.send_sms(
            phone=clean_phone,
            message=sms_message,
            subject='【iCHEF】'
        )
        
        # 更新 Firestore
        case_ref = db.collection('cases').document(case_id)
        
        if result['success']:
            # 發送成功
            case_ref.update({
                'delivery.smsSentAt': firestore.SERVER_TIMESTAMP,
                'delivery.smsStatus': 'sent',
                'delivery.smsBatchId': result.get('batch_id'),
                'delivery.smsPhone': clean_phone,
                'delivery.summaryUrl': summary_url,
                'delivery.smsCost': result.get('cost'),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"SMS sent successfully for case {case_id}, batch_id: {result.get('batch_id')}")
            
            return jsonify({
                'success': True,
                'caseId': case_id,
                'phone': clean_phone,
                'summaryUrl': summary_url,
                'batchId': result.get('batch_id'),
                'cost': result.get('cost')
            }), 200
        else:
            # 發送失敗
            case_ref.update({
                'delivery.smsStatus': 'failed',
                'delivery.smsError': result.get('error'),
                'delivery.smsErrorCode': result.get('error_code'),
                'delivery.smsPhone': clean_phone,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            logger.error(f"SMS sending failed for case {case_id}: {result.get('error')}")
            
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'errorCode': result.get('error_code')
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending SMS for case {case_id}: {e}", exc_info=True)
        
        # 記錄錯誤到 Firestore
        try:
            case_ref = db.collection('cases').document(case_id)
            case_ref.update({
                'delivery.smsStatus': 'error',
                'delivery.smsError': str(e),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
        except Exception as db_error:
            logger.error(f"Failed to update Firestore: {db_error}")
        
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
