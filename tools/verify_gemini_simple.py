import os
import time
import google.generativeai as genai

# 1. 設定 API Key
# 您可以在終端機執行: export GEMINI_API_KEY="您的_API_KEY"
# 或者直接將 Key 貼在下方 (測試完請記得刪除):
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ 錯誤: 未找到 GEMINI_API_KEY 環境變數。")
    print("請先執行: export GEMINI_API_KEY='your_api_key'")
    exit(1)

genai.configure(api_key=API_KEY)

def transcribe_file(file_path):
    print(f"📂 準備轉錄檔案: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 錯誤: 找不到檔案 {file_path}")
        return

    try:
        # 2. 上傳檔案
        print("⬆️  正在上傳檔案到 Gemini...")
        audio_file = genai.upload_file(file_path)
        
        # 等待處理
        while audio_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
        print("\n✅ 檔案處理完成")

        if audio_file.state.name == "FAILED":
            print("❌ 檔案處理失敗")
            return

        # 3. 發送 Prompt
        print("🤖 正在請求 Gemini 轉錄 (模型: gemini-1.5-flash)...")
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        prompt = "請將這段音訊轉錄為繁體中文逐字稿。請直接輸出內容，不要加任何開場白。"
        
        response = model.generate_content(
            [audio_file, prompt],
            generation_config={"temperature": 0.2}
        )
        
        print("\n" + "="*30)
        print("📝 轉錄結果:")
        print("="*30)
        print(response.text)
        print("="*30)

        # 清理
        genai.delete_file(audio_file.name)

    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")

if __name__ == "__main__":
    # 替換為您想測試的本地檔案路徑
    # 您可以先用 tools/inspect_audio.py 下載檔案到本地 temp_audio.m4a
    TARGET_FILE = "temp_audio.m4a" 
    
    if not os.path.exists(TARGET_FILE):
        print(f"⚠️  找不到 {TARGET_FILE}，請先確認檔案存在，或修改程式碼中的 TARGET_FILE 路徑。")
    else:
        transcribe_file(TARGET_FILE)
