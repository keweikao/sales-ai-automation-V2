"""
監控特定案件的處理狀態，並在完成時發送 Email 通知
"""
import time
from datetime import datetime
from google.cloud import firestore

# Configuration
CHECK_INTERVAL = 30  # seconds between checks
MAX_WAIT_TIME = 3600  # maximum wait time in seconds (1 hour)

def get_latest_case(db, customer_name_hint=None):
    """Get the latest case, optionally filtering by customer name"""
    cases_ref = db.collection("cases")
    
    # Get most recent cases
    query = cases_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(10)
    cases = list(query.stream())
    
    if customer_name_hint:
        for doc in cases:
            data = doc.to_dict()
            if customer_name_hint.lower() in data.get('customerName', '').lower():
                return doc.id, data
    
    # Return the most recent one
    if cases:
        return cases[0].id, cases[0].to_dict()
    return None, None

def get_case_status(db, case_id):
    """Get current status of a case"""
    doc_ref = db.collection("cases").document(case_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def format_status_report(case_id, data):
    """Format case data into a readable report"""
    status = data.get('status', 'unknown')
    customer_name = data.get('customerName', 'N/A')
    
    report = f"""
📋 案件狀態報告
{'=' * 50}
案件 ID: {case_id}
客戶名稱: {customer_name}
目前狀態: {status}
更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Add transcription info if available
    transcription = data.get('transcription')
    if transcription:
        text = transcription.get('text', '')
        if text:
            report += f"\n📝 轉錄文字長度: {len(text)} 字元"
            report += f"\n轉錄摘要 (前 500 字):\n{text[:500]}..."
    
    # Add analysis info if available
    analysis = data.get('analysis')
    if analysis:
        agents = analysis.get('agents', {})
        report += "\n\n🤖 Agent 分析結果:"
        for agent_name, agent_data in agents.items():
            if agent_data:
                report += f"\n  - {agent_name}: ✅ 完成"
        
        customer_summary = analysis.get('customerSummary', {})
        if customer_summary:
            markdown = customer_summary.get('markdown', '')
            if markdown:
                report += f"\n\n📄 客戶摘要:\n{markdown[:1000]}..."
    
    return report

def send_email_notification(subject, body, to_email):
    """Send email notification using Gmail SMTP"""
    # Note: This requires app password setup for Gmail
    # For now, we'll just print the notification
    print(f"\n{'=' * 60}")
    print("📧 EMAIL 通知")
    print(f"{'=' * 60}")
    print(f"收件人: {to_email}")
    print(f"主旨: {subject}")
    print(f"\n內容:\n{body}")
    print(f"{'=' * 60}")
    return True

def monitor_case(case_id, customer_name, email=None):
    """Monitor a case until it reaches a final status"""
    db = firestore.Client(project='sales-ai-automation-v2')
    
    start_time = time.time()
    last_status = None
    
    print(f"\n🔍 開始監控案件: {case_id}")
    print(f"   客戶: {customer_name}")
    print(f"   檢查間隔: {CHECK_INTERVAL} 秒")
    print(f"   最長等待: {MAX_WAIT_TIME} 秒")
    print("-" * 50)
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > MAX_WAIT_TIME:
            print(f"\n⏰ 已超過最長等待時間 ({MAX_WAIT_TIME} 秒)")
            break
        
        data = get_case_status(db, case_id)
        if not data:
            print(f"❌ 找不到案件: {case_id}")
            break
        
        current_status = data.get('status', 'unknown')
        
        # Print status if changed
        if current_status != last_status:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] 狀態更新: {last_status} → {current_status}")
            last_status = current_status
        
        # Check if processing is complete
        if current_status in ['completed', 'analyzed', 'analysis_completed']:
            print(f"\n✅ 處理完成！最終狀態: {current_status}")
            report = format_status_report(case_id, data)
            print(report)
            
            if email:
                send_email_notification(
                    subject=f"[Sales AI] 案件處理完成 - {customer_name}",
                    body=report,
                    to_email=email
                )
            return True
        
        # Check for failure status
        if 'failed' in current_status or 'error' in current_status:
            print(f"\n❌ 處理失敗！狀態: {current_status}")
            report = format_status_report(case_id, data)
            print(report)
            
            if email:
                send_email_notification(
                    subject=f"[Sales AI] ⚠️ 案件處理失敗 - {customer_name}",
                    body=report,
                    to_email=email
                )
            return False
        
        # Wait before next check
        time.sleep(CHECK_INTERVAL)
        print(".", end="", flush=True)
    
    return False

if __name__ == "__main__":
    db = firestore.Client(project='sales-ai-automation-v2')
    
    # Directly monitor this specific case
    case_id = "202601-IC001"
    customer_name = "知事官邸"
    
    # Get initial status
    data = get_case_status(db, case_id)
    if data:
        print(f"✅ 找到案件: {case_id}")
        print(f"   客戶: {data.get('customerName', 'N/A')}")
        print(f"   狀態: {data.get('status', 'unknown')}")
        print(f"   建立時間: {data.get('createdAt', 'N/A')}")
        
        # Start monitoring
        monitor_case(
            case_id=case_id,
            customer_name=customer_name,
            email="keweikao@gmail.com"
        )
    else:
        print(f"❌ 找不到案件: {case_id}")

