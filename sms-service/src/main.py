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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
# 規格書指定: 企業用戶使用 api.e8d.tw
EVERY8D_API_URL = os.getenv('EVERY8D_API_URL', 'https://api.e8d.tw/API21/HTTP/SendSMS.ashx')
SUMMARY_BASE_URL = os.getenv('SUMMARY_BASE_URL', 'https://summary-web-service-497329205771.asia-east1.run.app')
INTERNAL_TOKEN = os.getenv('SMS_INTERNAL_TOKEN')

# Gmail SMTP 設定
GMAIL_SENDER_EMAIL = os.getenv('GMAIL_SENDER_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')  # 需使用應用程式密碼

# 初始化 Firestore
db = firestore.Client(project=GCP_PROJECT_ID)


class EVERY8DSMSService:
    """互動資通 EVERY8D SMS API21 整合"""
    
    def __init__(self, username: str, password: str, api_url: str = None):
        self.username = username
        self.password = password
        # 規格書指定: 企業用戶使用 api.e8d.tw
        self.api_url = api_url or 'https://api.e8d.tw/API21/HTTP/SendSMS.ashx'
    
    def send_sms(
        self,
        phone: str,
        message: str,
        subject: str = '【iCHEF】'
    ) -> Dict[str, Any]:
        """
        發送簡訊 (API21 規格)
        
        Args:
            phone: 手機號碼 (09xxxxxxxx)
            message: 簡訊內容
            subject: 簡訊主旨（選填，僅供記錄）
        
        Returns:
            發送結果字典
        """
        # 準備 API 參數 (application/x-www-form-urlencoded)
        data = {
            'UID': self.username,
            'PWD': self.password,
            'SB': subject,
            'MSG': message,
            'DEST': phone,
            'ST': '',  # 空字串表示立即發送
            'RETRYTIME': '1440',  # 有效期限 1440 分鐘
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            logger.info(f"Sending SMS to {phone} via {self.api_url}")
            logger.info(f"Message length: {len(message)} characters")
            
            # 使用 POST 方法 (規格書要求)
            response = requests.post(
                self.api_url, 
                data=data,
                headers=headers,
                timeout=30
            )
            result = response.text.strip()
            
            logger.info(f"EVERY8D API response: {result}")
            
            # 解析回應
            if ',' in result and not result.startswith('-'):
                # 成功：格式為 CREDIT,SENDED,COST,UNSEND,BATCHID
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
            
            # 失敗回應格式: Status,Msg (例: -99,發生不明錯誤)
            if ',' in result:
                parts = result.split(',', 1)
                error_code = parts[0]
                error_msg = parts[1] if len(parts) > 1 else '未知錯誤'
            else:
                error_code = result
                error_msg = self._get_error_message(result)
            
            logger.error(f"EVERY8D API error: {error_code} - {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code
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
    
    def _get_error_message(self, error_code: str) -> str:
        """取得錯誤代碼對應的訊息"""
        error_codes = {
            '-1': '帳號密碼錯誤',
            '-2': '餘額不足',
            '-3': '簡訊內容不得為空白',
            '-4': '無效的手機號碼',
            '-5': '內容數超過限制',
            '-6': '門號數超過限制',
            '-7': '簡訊內容含有非法字元',
            '-8': '發送時間格式錯誤',
            '-9': '效期時間超過限制',
            '-10': '活動代碼無效',
            '-99': '系統發生錯誤',
            '-100': '系統維護中'
        }
        return error_codes.get(error_code, f'未知錯誤: {error_code}')


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


def generate_short_url(case_id: str, target_url: str) -> str:
    """
    生成短網址並儲存到 Firestore
    
    Args:
        case_id: 案件 ID
        target_url: 目標完整 URL
    
    Returns:
        短網址
    """
    import secrets
    import string
    
    case_ref = db.collection('cases').document(case_id)
    case_doc = case_ref.get()
    
    if case_doc.exists:
        case_data = case_doc.to_dict() or {}
        delivery = case_data.get('delivery', {})
        existing_short_url = delivery.get('shortUrl')
        if existing_short_url:
            logger.info(f"Using existing short URL for case {case_id}: {existing_short_url}")
            return existing_short_url
    
    # 生成短代碼
    alphabet = string.ascii_letters + string.digits
    for _ in range(5):
        code = ''.join(secrets.choice(alphabet) for _ in range(7))
        short_ref = db.collection('shortUrls').document(code)
        
        if not short_ref.get().exists:
            short_url = f"{SUMMARY_BASE_URL}/s/{code}"
            short_ref.set({
                'caseId': case_id,
                'targetUrl': target_url,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'clickCount': 0,
                'active': True,
            })
            case_ref.update({
                'delivery.shortUrl': short_url,
                'delivery.shortCode': code,
                'delivery.summaryPageUrl': target_url,
            })
            logger.info(f"Created short URL for case {case_id}: {short_url}")
            return short_url
    
    # 如果生成失敗，返回原始 URL
    logger.warning(f"Failed to generate short URL for case {case_id}, using original URL")
    return target_url


def compose_sms_message(customer_name: str, summary_url: str) -> str:
    """
    組合簡訊內容
    
    Args:
        customer_name: 客戶姓名
        summary_url: 網頁 URL (短網址)
    
    Returns:
        簡訊內容
    """
    # 簡訊內容（中文標準簡訊 70 字以內，盡量簡潔）
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
        # 生成完整網頁 URL
        full_summary_url = generate_summary_url(case_id)
        
        # 生成短網址
        summary_url = generate_short_url(case_id, full_summary_url)
        
        # 組合簡訊內容
        sms_message = compose_sms_message(customer_name, summary_url)
        
        logger.info(f"Sending SMS for case {case_id} to {clean_phone}")
        logger.info(f"Short URL: {summary_url}")
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


@app.route('/send-email', methods=['POST'])
def send_email():
    """
    發送會議記錄 Email
    
    請求格式:
    {
        "caseId": "202512-IC001",
        "customerEmail": "customer@example.com",
        "customerName": "一畝食鍋老闆"
    }
    """
    # 驗證 Token
    auth_header = request.headers.get('Authorization', '')
    if INTERNAL_TOKEN and not auth_header.endswith(INTERNAL_TOKEN):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        
        case_id = data.get('caseId')
        customer_email = data.get('customerEmail')
        customer_name = data.get('customerName', '客戶')
        
        if not case_id:
            return jsonify({'error': 'Missing caseId'}), 400
        if not customer_email:
            return jsonify({'error': 'Missing customerEmail'}), 400
        
        logger.info(f"Sending email for case {case_id} to {customer_email}")
        
        # 檢查 Gmail 設定
        if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
            logger.error("Gmail SMTP not configured")
            return jsonify({'error': 'Email service not configured'}), 500
        
        # 生成摘要 URL
        summary_url = generate_summary_url(case_id)
        short_url = generate_short_url(case_id, summary_url)
        
        # 組建 Email 內容
        subject = f"【iCHEF】{customer_name} 會議重點摘要"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍽️ iCHEF</h1>
            <p>會議重點摘要</p>
        </div>
        <div class="content">
            <p>親愛的 {customer_name} 您好，</p>
            <p>感謝您今天撥冗與我們討論！</p>
            <p>我們已為您整理了會議的重點摘要，請點擊下方按鈕查看：</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{short_url}" class="button">📋 查看會議摘要</a>
            </p>
            <p>如有任何問題，歡迎隨時與我們聯繫！</p>
            <p>祝 生意興隆</p>
            <p><strong>iCHEF 團隊</strong></p>
        </div>
        <div class="footer">
            <p>此信件由 iCHEF 系統自動發送</p>
            <p>案件編號: {case_id}</p>
        </div>
    </div>
</body>
</html>
"""
        
        # 發送 Email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_SENDER_EMAIL
        msg['To'] = customer_email
        
        # 純文字版本
        text_content = f"""
親愛的 {customer_name} 您好，

感謝您今天撥冗與我們討論！

我們已為您整理了會議的重點摘要，請點擊以下連結查看：
{short_url}

如有任何問題，歡迎隨時與我們聯繫！

祝 生意興隆
iCHEF 團隊

---
案件編號: {case_id}
"""
        
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # 使用 Gmail SMTP 發送
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER_EMAIL, customer_email, msg.as_string())
        
        logger.info(f"Email sent successfully for case {case_id}")
        
        # 更新 Firestore
        try:
            case_ref = db.collection('cases').document(case_id)
            case_ref.update({
                'delivery.emailStatus': 'sent',
                'delivery.emailSentAt': firestore.SERVER_TIMESTAMP,
                'delivery.emailTo': customer_email,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
        except Exception as db_error:
            logger.error(f"Failed to update Firestore: {db_error}")
        
        return jsonify({
            'status': 'success',
            'message': f'Email sent to {customer_email}',
            'caseId': case_id,
            'summaryUrl': short_url
        }), 200
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Gmail authentication failed: {e}")
        return jsonify({'error': 'Email authentication failed'}), 500
    except Exception as e:
        logger.error(f"Email sending failed for case {case_id}: {e}", exc_info=True)
        
        # 更新 Firestore 錯誤狀態
        try:
            case_ref = db.collection('cases').document(case_id)
            case_ref.update({
                'delivery.emailStatus': 'failed',
                'delivery.emailError': str(e),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
        except Exception as db_error:
            logger.error(f"Failed to update Firestore: {db_error}")
        
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
