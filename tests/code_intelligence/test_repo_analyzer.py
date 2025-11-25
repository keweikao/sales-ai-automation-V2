"""
測試專案分析器功能
"""

import pytest
from pathlib import Path
import sys

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "tools" / "code_intelligence"))

try:
    from repo_analyzer import SalesAIRepoAnalyzer
    KIT_AVAILABLE = True
except ImportError:
    KIT_AVAILABLE = False


@pytest.mark.skipif(not KIT_AVAILABLE, reason="kit-ai 套件未安裝")
class TestSalesAIRepoAnalyzer:
    """測試專案分析器"""
    
    @pytest.fixture
    def analyzer(self):
        """建立分析器實例"""
        return SalesAIRepoAnalyzer(repo_path=str(project_root))
    
    def test_initialization(self, analyzer):
        """測試初始化"""
        assert analyzer is not None
        assert analyzer.repo is not None
        assert analyzer.repo_path.exists()
    
    def test_find_agent_implementations(self, analyzer):
        """測試找出 AI 代理"""
        agents = analyzer.find_agent_implementations()
        
        # 應該至少找到一些代理
        assert isinstance(agents, list)
        # 專案中應該有 7 個代理
        assert len(agents) > 0
    
    def test_extract_api_endpoints(self, analyzer):
        """測試提取 API 端點"""
        endpoints = analyzer.extract_api_endpoints()
        
        # 應該找到一些端點
        assert isinstance(endpoints, list)
        assert len(endpoints) > 0
    
    def test_get_file_tree(self, analyzer):
        """測試獲取檔案樹"""
        result = analyzer.get_file_tree()
        
        assert result["status"] == "success"
        assert "tree" in result
    
    def test_get_file_tree_subdirectory(self, analyzer):
        """測試獲取子目錄的檔案樹"""
        result = analyzer.get_file_tree(subdirectory="src")
        
        assert result["status"] == "success"
        assert "tree" in result
    
    def test_extract_symbols(self, analyzer):
        """測試提取符號"""
        # 提取特定檔案的符號
        symbols = analyzer.extract_symbols(
            file_path="src/transcription/main.py"
        )
        
        assert isinstance(symbols, list)
        # 應該至少有一些函數或類別
        assert len(symbols) > 0
        
        # 檢查符號結構
        if symbols:
            symbol = symbols[0]
            assert "name" in symbol
            assert "type" in symbol
            assert "file" in symbol


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
