#!/usr/bin/env python3
"""
AI 助手自動初始化腳本
在每次 AI 助手啟動時自動執行，確保程式碼智能工具就緒
"""

import sys
import subprocess
from pathlib import Path

def check_and_build_index():
    """檢查並建立程式碼索引"""
    # tools/code_intelligence/auto_init.py -> tools/code_intelligence -> tools -> project_root
    project_root = Path(__file__).parent.parent.parent
    index_file = project_root / ".kit-mcp" / "cache" / "symbol_index.json"
    
    # 檢查索引是否存在
    if index_file.exists():
        print("✓ 程式碼索引已存在")
        return True
    
    print("⚙️  首次執行：正在建立程式碼索引...")
    
    try:
        # 執行索引建立
        cli_path = project_root / "tools" / "code_intelligence" / "cli.py"
        result = subprocess.run(
            ["python3", str(cli_path), "build-index"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✓ 程式碼索引建立完成")
            return True
        else:
            print(f"⚠️  索引建立失敗: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠️  索引建立錯誤: {e}")
        return False

def check_dependencies():
    """檢查必要的依賴是否已安裝"""
    try:
        import kit  # noqa: F401
        return True
    except ImportError:
        print("⚠️  cased-kit 未安裝")
        print("   請執行: pip install -r tools/code_intelligence/requirements.txt")
        return False

def main():
    """主函數"""
    print("=" * 60)
    print("🤖 AI 助手自動初始化")
    print("=" * 60)
    
    # 1. 檢查依賴
    if not check_dependencies():
        print("\n❌ 初始化失敗：缺少必要依賴")
        return False
    
    # 2. 建立索引
    check_and_build_index()
    
    print("\n" + "=" * 60)
    print("✅ 初始化完成！程式碼智能工具已就緒")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
