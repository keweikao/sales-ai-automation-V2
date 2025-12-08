"""
測試 SMS 服務

使用方式:
    python test_sms_service.py --case-id 202512-IC001 --phone 0912345678 --name "測試客戶"
"""

import argparse
import requests
import os

def test_sms_service(case_id: str, phone: str, name: str):
    """測試 SMS 服務"""
    
    # SMS 服務 URL
    sms_service_url = os.getenv(
        'SMS_SERVICE_URL',
        'http://localhost:8080'  # 本地測試
    )
    
    # 內部 token
    internal_token = os.getenv('SMS_INTERNAL_TOKEN', '')
    
    # 準備請求
    url = f"{sms_service_url}/send-sms"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {internal_token}' if internal_token else ''
    }
    payload = {
        'caseId': case_id,
        'customerPhone': phone,
        'customerName': name
    }
    
    print(f"📤 發送測試請求到: {url}")
    print(f"📋 請求內容: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 回應狀態: {response.status_code}")
        print(f"📄 回應內容:")
        print(response.json())
        
        if response.status_code == 200:
            print("\n✅ SMS 發送成功！")
        else:
            print(f"\n❌ SMS 發送失敗: {response.status_code}")
            
    except requests.RequestException as e:
        print(f"\n❌ 請求失敗: {e}")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='測試 SMS 服務')
    parser.add_argument('--case-id', required=True, help='案件 ID')
    parser.add_argument('--phone', required=True, help='客戶電話 (09xxxxxxxx)')
    parser.add_argument('--name', required=True, help='客戶姓名')
    
    args = parser.parse_args()
    
    test_sms_service(args.case_id, args.phone, args.name)
