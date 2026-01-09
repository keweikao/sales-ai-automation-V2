"""
符號索引器 - 建立可搜尋的程式碼符號索引
"""

import json
from typing import Dict, List
from pathlib import Path

try:
    from kit import Repository, DocstringIndexer, SummarySearcher
except ImportError:
    print("警告: kit-ai 套件未安裝。請執行: pip install kit-ai")
    Repository = DocstringIndexer = SummarySearcher = None


class SmartCodeSearch:
    """智能程式碼搜尋系統"""
    
    def __init__(self, repo_path: str = ".", cache_dir: str = ".kit-mcp/cache"):
        """
        初始化智能搜尋系統
        
        Args:
            repo_path: 專案根目錄路徑
            cache_dir: 快取目錄路徑
        """
        if Repository is None:
            raise ImportError("需要安裝 kit-ai 套件")
            
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.repo = Repository(str(self.repo_path))
        self.index_file = self.cache_dir / "symbol_index.json"
        self.indexer = None
        self.searcher = None
    
    def build_index(self, force_rebuild: bool = False) -> Dict:
        """
        建立整個專案的符號索引
        
        Args:
            force_rebuild: 是否強制重建索引
            
        Returns:
            索引建立結果
        """
        if self.index_file.exists() and not force_rebuild:
            return {
                "status": "skipped",
                "message": "索引已存在，使用 force_rebuild=True 強制重建"
            }
        
        try:
            print("正在建立符號索引...")
            
            # 提取所有符號
            symbols = self.repo.extract_symbols()
            
            # 建立索引
            index_data = {
                "symbols": [],
                "total_count": len(symbols)
            }
            
            for symbol in symbols:
                index_data["symbols"].append({
                    "name": symbol["name"],
                    "type": symbol["type"],
                    "file": symbol["file"],
                    "line_start": symbol["start_line"],
                    "line_end": symbol["end_line"]
                })
            
            # 儲存索引
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 索引建立完成，共 {len(symbols)} 個符號")
            
            return {
                "status": "success",
                "total_symbols": len(symbols),
                "index_file": str(self.index_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        使用自然語言搜尋程式碼
        
        Args:
            query: 搜尋查詢
            limit: 結果數量限制
            
        Returns:
            搜尋結果列表
        """
        if not self.index_file.exists():
            print("索引不存在，請先執行 build_index()")
            return []
        
        try:
            # 載入索引
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 簡單的關鍵字搜尋（未來可以整合 LLM）
            results = []
            query_lower = query.lower()
            
            for symbol in index_data["symbols"]:
                # 搜尋符號名稱
                if query_lower in symbol["name"].lower():
                    results.append(symbol)
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            print(f"錯誤: {e}")
            return []
    
    def search_by_type(self, symbol_type: str) -> List[Dict]:
        """
        根據符號類型搜尋
        
        Args:
            symbol_type: 符號類型 (function, class, method, etc.)
            
        Returns:
            搜尋結果列表
        """
        if not self.index_file.exists():
            print("索引不存在，請先執行 build_index()")
            return []
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            results = [
                symbol for symbol in index_data["symbols"]
                if symbol["type"] == symbol_type
            ]
            
            return results
            
        except Exception as e:
            print(f"錯誤: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        獲取索引統計資訊
        
        Returns:
            統計資訊
        """
        if not self.index_file.exists():
            return {
                "status": "no_index",
                "message": "索引不存在"
            }
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 統計各類型符號數量
            type_counts = {}
            for symbol in index_data["symbols"]:
                symbol_type = symbol["type"]
                type_counts[symbol_type] = type_counts.get(symbol_type, 0) + 1
            
            return {
                "status": "success",
                "total_symbols": index_data["total_count"],
                "type_distribution": type_counts,
                "index_file": str(self.index_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


if __name__ == "__main__":
    # 簡單測試
    searcher = SmartCodeSearch()
    
    print("=== 建立索引 ===")
    result = searcher.build_index()
    print(f"結果: {result}")
    
    print("\n=== 搜尋 'Agent' ===")
    results = searcher.search("Agent", limit=5)
    for r in results:
        print(f"  {r['name']} ({r['type']}) - {r['file']}:{r['line_start']}")
    
    print("\n=== 索引統計 ===")
    stats = searcher.get_stats()
    print(f"總符號數: {stats.get('total_symbols', 0)}")
    print(f"類型分布: {stats.get('type_distribution', {})}")
