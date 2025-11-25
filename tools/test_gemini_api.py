#!/usr/bin/env python3
"""
Gemini API 驗證腳本
測試 Vertex AI Gemini API 是否正常運作
"""

import os
import sys
import logging
from pathlib import Path

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_vertex_ai_gemini():
    """測試 Vertex AI Gemini API"""
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        # 檢查專案 ID
        project_id = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
        location = "asia-east1"
        
        logger.info(f"初始化 Vertex AI (Project: {project_id}, Location: {location})")
        
        # 初始化 Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # 載入模型
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        logger.info(f"載入模型: {model_name}")
        model = GenerativeModel(model_name)
        
        # 測試簡單的文字生成
        logger.info("測試文字生成...")
        response = model.generate_content(
            "請用繁體中文回答：你好嗎？",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 100,
            }
        )
        
        logger.info(f"✅ Gemini API 回應成功！")
        logger.info(f"回應內容: {response.text[:100]}...")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 缺少必要的套件: {e}")
        logger.error("請執行: pip install google-cloud-aiplatform")
        return False
        
    except Exception as e:
        logger.error(f"❌ Gemini API 測試失敗: {e}", exc_info=True)
        return False

def test_google_ai_gemini():
    """測試 Google AI Gemini API (需要 API Key)"""
    try:
        import google.generativeai as genai
        
        # 檢查 API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("⚠️  GEMINI_API_KEY 未設定，跳過 Google AI API 測試")
            return None
        
        logger.info("測試 Google AI Gemini API...")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Hello, how are you?")

        
        logger.info(f"✅ Google AI Gemini API 回應成功！")
        logger.info(f"回應內容: {response.text[:100]}...")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 缺少必要的套件: {e}")
        logger.error("請執行: pip install google-generativeai")
        return False
        
    except Exception as e:
        logger.error(f"❌ Google AI Gemini API 測試失敗: {e}", exc_info=True)
        return False

def main():
    """主函數"""
    print("=" * 60)
    print("🔍 Gemini API 驗證測試")
    print("=" * 60)
    print()
    
    # 顯示環境資訊
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"GCP_PROJECT_ID: {os.getenv('GCP_PROJECT_ID', 'Not set')}")
    logger.info(f"GEMINI_MODEL: {os.getenv('GEMINI_MODEL', 'Not set')}")
    logger.info(f"GEMINI_API_KEY: {'已設定' if os.getenv('GEMINI_API_KEY') else '未設定'}")
    print()
    
    # 測試 Vertex AI Gemini (用於 Transcription Service)
    print("-" * 60)
    print("測試 1: Vertex AI Gemini (Transcription Service 使用)")
    print("-" * 60)
    vertex_result = test_vertex_ai_gemini()
    print()
    
    # 測試 Google AI Gemini (用於 Analysis Service)
    print("-" * 60)
    print("測試 2: Google AI Gemini (Analysis Service 使用)")
    print("-" * 60)
    google_ai_result = test_google_ai_gemini()
    print()
    
    # 總結
    print("=" * 60)
    print("📊 測試結果總結")
    print("=" * 60)
    print(f"Vertex AI Gemini (Transcription): {'✅ 通過' if vertex_result else '❌ 失敗'}")
    print(f"Google AI Gemini (Analysis): {'✅ 通過' if google_ai_result else '⚠️  跳過' if google_ai_result is None else '❌ 失敗'}")
    print()
    
    if vertex_result:
        print("✅ Transcription Service 的 Gemini API 正常運作！")
    else:
        print("❌ Transcription Service 的 Gemini API 有問題，請檢查：")
        print("   1. GCP 專案 ID 是否正確")
        print("   2. 服務帳號是否有 Vertex AI 權限")
        print("   3. Vertex AI API 是否已啟用")
    
    return 0 if vertex_result else 1

if __name__ == "__main__":
    sys.exit(main())
