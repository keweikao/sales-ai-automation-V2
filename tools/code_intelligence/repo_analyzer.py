"""
專案分析器 - 使用 Cased Kit 分析 Sales AI Automation 專案
"""

from typing import Dict, List, Optional
from pathlib import Path

try:
    from kit import Repository
except ImportError:
    print("警告: kit-ai 套件未安裝。請執行: pip install kit-ai")
    Repository = None


class SalesAIRepoAnalyzer:
    """Sales AI Automation 專案分析器"""
    
    def __init__(self, repo_path: str = "."):
        """
        初始化專案分析器
        
        Args:
            repo_path: 專案根目錄路徑
        """
        if Repository is None:
            raise ImportError("需要安裝 kit-ai 套件")
            
        self.repo_path = Path(repo_path).resolve()
        self.repo = Repository(str(self.repo_path))
    
    def analyze_service_dependencies(self) -> Dict:
        """
        分析服務間的依賴關係
        
        Returns:
            依賴關係報告
        """
        try:
            analyzer = self.repo.get_dependency_analyzer()
            report = analyzer.generate_dependency_report()
            return {
                "status": "success",
                "report": report
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def find_agent_implementations(self) -> List[Dict]:
        """
        找出所有 AI 代理的實作
        
        Returns:
            代理實作列表
        """
        try:
            # 搜尋 Agent 類別定義（使用正則表達式）
            results = self.repo.search_text(
                query=r"class Agent\d+"
            )
            
            agents = []
            for result in results:
                agents.append({
                    "file": result["file"],
                    "line": result["line_number"],
                    "content": result["line"]
                })
            
            return agents
        except Exception as e:
            print(f"錯誤: {e}")
            return []
    
    def extract_api_endpoints(self) -> List[Dict]:
        """
        提取所有 API 端點
        
        Returns:
            API 端點列表
        """
        try:
            # 搜尋 Flask/FastAPI 路由定義
            patterns = [
                r"@(app|flask_app)\.(route|post|get|put|delete)",
                r"@router\.(post|get|put|delete)"
            ]
            
            endpoints = []
            for pattern in patterns:
                results = self.repo.search_text(
                    query=pattern
                )
                
                for result in results:
                    endpoints.append({
                        "file": result["file"],
                        "line": result["line_number"],
                        "content": result["line"]
                    })
            
            return endpoints
        except Exception as e:
            print(f"錯誤: {e}")
            return []
    
    def find_symbol_usages(self, symbol_name: str, file_path: Optional[str] = None) -> List[Dict]:
        """
        追蹤特定符號的使用位置
        
        Args:
            symbol_name: 符號名稱
            file_path: 可選的檔案路徑
            
        Returns:
            符號使用位置列表
        """
        try:
            usages = self.repo.find_symbol_usages(
                symbol_name=symbol_name,
                file_path=file_path
            )
            
            results = []
            for usage in usages:
                results.append({
                    "file": usage.file_path,
                    "line": usage.line_number,
                    "context": usage.context
                })
            
            return results
        except Exception as e:
            print(f"錯誤: {e}")
            return []
    
    def get_file_tree(self, subdirectory: Optional[str] = None) -> Dict:
        """
        獲取檔案樹結構

        Args:
            subdirectory: 可選的子目錄

        Returns:
            檔案樹結構
        """
        try:
            # kit-ai API 返回字典列表，每個字典有 path 屬性
            tree = self.repo.get_file_tree()
            if subdirectory:
                # 過濾只保留指定子目錄的內容
                filtered_tree = [
                    item for item in tree
                    if item.get("path", "").startswith(subdirectory + "/")
                    or item.get("path", "") == subdirectory
                ]
                tree = filtered_tree
            return {
                "status": "success",
                "tree": tree
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def extract_symbols(self, file_path: Optional[str] = None) -> List[Dict]:
        """
        提取符號（函數、類別等）
        
        Args:
            file_path: 可選的檔案路徑
            
        Returns:
            符號列表
        """
        try:
            symbols = self.repo.extract_symbols(file_path=file_path)
            
            results = []
            for symbol in symbols:
                results.append({
                    "name": symbol["name"],
                    "type": symbol["type"],
                    "file": symbol["file"],
                    "line_start": symbol["start_line"],
                    "line_end": symbol["end_line"]
                })
            
            return results
        except Exception as e:
            print(f"錯誤: {e}")
            return []


if __name__ == "__main__":
    # 簡單測試
    analyzer = SalesAIRepoAnalyzer()
    
    print("=== 找出所有 AI 代理 ===")
    agents = analyzer.find_agent_implementations()
    for agent in agents[:5]:  # 只顯示前 5 個
        print(f"  {agent['file']}:{agent['line']} - {agent['content']}")
    
    print(f"\n總共找到 {len(agents)} 個代理")
