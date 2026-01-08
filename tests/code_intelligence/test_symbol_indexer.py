"""
測試符號索引器功能
"""

import pytest
from pathlib import Path
import sys
import json

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "tools" / "code_intelligence"))

try:
    import symbol_indexer as _symbol_indexer

    SmartCodeSearch = _symbol_indexer.SmartCodeSearch
    # If kit-ai is not installed, symbol_indexer will set Repository to None.
    KIT_AVAILABLE = _symbol_indexer.Repository is not None
except Exception:
    KIT_AVAILABLE = False


@pytest.mark.skipif(not KIT_AVAILABLE, reason="kit-ai 套件未安裝")
class TestSmartCodeSearch:
    """測試符號索引器"""
    
    @pytest.fixture
    def searcher(self, tmp_path):
        """建立搜尋器實例"""
        cache_dir = tmp_path / "cache"
        return SmartCodeSearch(
            repo_path=str(project_root),
            cache_dir=str(cache_dir)
        )
    
    def test_initialization(self, searcher):
        """測試初始化"""
        assert searcher is not None
        assert searcher.repo is not None
        assert searcher.cache_dir.exists()
    
    def test_build_index(self, searcher):
        """測試建立索引"""
        result = searcher.build_index(force_rebuild=True)
        
        assert result["status"] == "success"
        assert result["total_symbols"] > 0
        assert searcher.index_file.exists()
        
        # 驗證索引檔案格式
        with open(searcher.index_file, 'r') as f:
            index_data = json.load(f)
        
        assert "symbols" in index_data
        assert "total_count" in index_data
        assert len(index_data["symbols"]) > 0
    
    def test_search(self, searcher):
        """測試搜尋功能"""
        # 先建立索引
        searcher.build_index(force_rebuild=True)
        
        # 搜尋 "Agent"
        results = searcher.search("Agent", limit=5)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 5
        
        # 檢查結果結構
        if results:
            result = results[0]
            assert "name" in result
            assert "type" in result
            assert "file" in result
    
    def test_search_by_type(self, searcher):
        """測試按類型搜尋"""
        # 先建立索引
        searcher.build_index(force_rebuild=True)
        
        # 搜尋所有類別
        results = searcher.search_by_type("class")
        
        assert isinstance(results, list)
        # 應該有一些類別
        assert len(results) > 0
    
    def test_get_stats(self, searcher):
        """測試獲取統計資訊"""
        # 先建立索引
        searcher.build_index(force_rebuild=True)
        
        stats = searcher.get_stats()
        
        assert stats["status"] == "success"
        assert stats["total_symbols"] > 0
        assert "type_distribution" in stats
        assert isinstance(stats["type_distribution"], dict)
    
    def test_search_without_index(self, searcher):
        """測試在沒有索引時搜尋"""
        results = searcher.search("test")
        
        # 應該返回空列表
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
